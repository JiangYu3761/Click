#import "ClickUpdates.h"
#import <Sparkle/Sparkle.h>

@interface ClickUpdateDriver : SPUStandardUserDriver
@end

@implementation ClickUpdateDriver
// The user already chose Install in the manual update dialog.
- (void)showReadyToInstallAndRelaunch:(void (^)(SPUUserUpdateChoice))reply {
    reply(SPUUserUpdateChoiceInstall);
}
@end

@interface ClickUpdates () <SPUUpdaterDelegate>
@property(nonatomic, strong) SPUUpdater *updater;
@property(nonatomic, strong) ClickUpdateDriver *driver;
@property(nonatomic, copy) BOOL (^canRestart)(void);
@property(nonatomic, strong) NSError *startupError;
@property(nonatomic, weak) NSButton *automaticButton;
@end

@implementation ClickUpdates
- (instancetype)initWithCanRestart:(BOOL (^)(void))canRestart {
    if ((self = [super init])) {
        _canRestart = [canRestart copy];
        _driver = [[ClickUpdateDriver alloc] initWithHostBundle:NSBundle.mainBundle delegate:nil];
        _updater = [[SPUUpdater alloc] initWithHostBundle:NSBundle.mainBundle applicationBundle:NSBundle.mainBundle userDriver:_driver delegate:self];
    }
    return self;
}
- (void)start {
    NSError *error = nil;
    if (![self.updater startUpdater:&error]) {
        self.startupError = error;
        return;
    }
    NSDate *lastCheck = self.updater.lastUpdateCheckDate;
    if (self.updater.automaticallyChecksForUpdates && self.updater.canCheckForUpdates &&
        (!lastCheck || -lastCheck.timeIntervalSinceNow >= self.updater.updateCheckInterval)) {
        [self.updater checkForUpdatesInBackground];
    }
}
- (BOOL)isAutomaticUpdateEnabled {
    return self.updater.automaticallyChecksForUpdates && self.updater.automaticallyDownloadsUpdates;
}
- (NSView *)makeLibraryControls {
    NSButton *automatic = [NSButton checkboxWithTitle:@"自动更新" target:self action:@selector(toggleAutomatic:)];
    automatic.controlSize = NSControlSizeSmall;
    automatic.state = self.isAutomaticUpdateEnabled ? NSControlStateValueOn : NSControlStateValueOff;
    automatic.toolTip = @"自动检查、下载并安装新版本，完成后重新打开 Click";
    self.automaticButton = automatic;
    NSButton *check = [NSButton buttonWithTitle:@"手动更新" target:self action:@selector(checkNow:)];
    check.controlSize = NSControlSizeSmall;
    check.toolTip = @"立即检查新版本";
    NSStackView *row = [NSStackView stackViewWithViews:@[automatic, check]];
    row.orientation = NSUserInterfaceLayoutOrientationHorizontal;
    row.spacing = 12;
    row.appearance = [NSAppearance appearanceNamed:NSAppearanceNameDarkAqua];
    return row;
}
- (void)addItemsToMenu:(NSMenu *)menu {
    [menu addItemWithTitle:@"检查更新…" action:@selector(checkNow:) keyEquivalent:@""].target = self;
    NSMenuItem *automatic = [menu addItemWithTitle:@"自动更新" action:@selector(toggleAutomatic:) keyEquivalent:@""];
    automatic.target = self;
    automatic.state = self.isAutomaticUpdateEnabled ? NSControlStateValueOn : NSControlStateValueOff;
    automatic.toolTip = @"定期检查新版本，下载完成后自动安装并重新打开 Click";
}
- (void)checkNow:(id)sender {
    if (self.startupError) {
        [[NSAlert alertWithError:self.startupError] runModal];
    } else {
        [self.updater checkForUpdates];
    }
}
- (void)toggleAutomatic:(id)sender {
    BOOL enabled = !self.isAutomaticUpdateEnabled;
    // Sparkle accepts a download opt-in only after automatic checks are enabled.
    if (!enabled) self.updater.automaticallyDownloadsUpdates = NO;
    self.updater.automaticallyChecksForUpdates = enabled;
    if (enabled) self.updater.automaticallyDownloadsUpdates = YES;
    NSControlStateValue state = self.isAutomaticUpdateEnabled ? NSControlStateValueOn : NSControlStateValueOff;
    [sender setState:state];
    self.automaticButton.state = state;
    if (enabled && self.updater.canCheckForUpdates) [self.updater checkForUpdatesInBackground];
}
- (BOOL)validateMenuItem:(NSMenuItem *)item {
    if (item.action == @selector(toggleAutomatic:)) {
        item.state = self.isAutomaticUpdateEnabled ? NSControlStateValueOn : NSControlStateValueOff;
        return self.startupError == nil;
    }
    return self.startupError != nil || self.updater.canCheckForUpdates;
}
- (BOOL)updater:(SPUUpdater *)updater willInstallUpdateOnQuit:(SUAppcastItem *)item immediateInstallationBlock:(void (^)(void))install {
    if (!updater.automaticallyChecksForUpdates || !updater.automaticallyDownloadsUpdates) return NO;
    // Run after Sparkle finishes recording its pending-update state.
    dispatch_async(dispatch_get_main_queue(), install);
    return YES;
}
- (BOOL)updater:(SPUUpdater *)updater shouldPostponeRelaunchForUpdate:(SUAppcastItem *)item untilInvokingBlock:(void (^)(void))install {
    if (self.canRestart()) return NO;
    [self installWhenReaderIsReady:install];
    return YES;
}
- (void)installWhenReaderIsReady:(void (^)(void))install {
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 2 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{
        if (self.canRestart()) install();
        else [self installWhenReaderIsReady:install];
    });
}
@end
