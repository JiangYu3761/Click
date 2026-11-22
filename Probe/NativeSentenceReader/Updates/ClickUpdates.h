#import <Cocoa/Cocoa.h>

NS_ASSUME_NONNULL_BEGIN
@interface ClickUpdates : NSObject <NSMenuItemValidation>
- (instancetype)initWithCanRestart:(BOOL (^)(void))canRestart;
- (void)addItemsToMenu:(NSMenu *)menu;
- (void)start;
@end
NS_ASSUME_NONNULL_END
