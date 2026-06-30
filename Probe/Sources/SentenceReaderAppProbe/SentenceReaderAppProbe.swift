import SwiftUI
import ReadiumProbe

@main
struct SentenceReaderAppProbe: App {
    var body: some Scene {
        WindowGroup {
            ReaderWorkspaceView(
                annotations: SampleData.annotations,
                book: SampleData.book
            )
            .frame(minWidth: 1040, minHeight: 680)
        }
        .windowStyle(.titleBar)
    }
}

private struct ReaderWorkspaceView: View {
    let annotations: [ReaderAnnotation]
    let book: BookReference

    @State private var selectedSentenceID: String? = SampleData.annotations.first?.sentenceID
    @State private var notesVisible = true
    @State private var draftNote = ""
    @State private var editorVisible = false

    var body: some View {
        VStack(spacing: 0) {
            toolbar
            Divider()
            HStack(spacing: 0) {
                leftSidebar
                    .frame(width: 242)
                Divider()
                readerPane
                    .frame(minWidth: 520)
                if notesVisible {
                    Divider()
                    notesRail
                        .frame(width: 312)
                }
            }
        }
        .sheet(isPresented: $editorVisible) {
            NoteEditorView(
                sourceText: selectedAnnotation?.sourceText ?? "",
                noteText: $draftNote
            )
            .frame(width: 520, height: 320)
        }
    }

    private var toolbar: some View {
        HStack(spacing: 10) {
            Button("打开书") {}
            Button {
                focusReaderEntry()
            } label: {
                Label("阅读入口", systemImage: "book.pages")
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.small)
            .keyboardShortcut("r", modifiers: [.command])
            .help("回到当前书正文")
            Spacer()
            Text("Sentence Reader · \(book.title)")
                .font(.headline)
                .lineLimit(1)
            Spacer()
            Text("本地保存")
                .font(.caption)
                .foregroundStyle(.green)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(.green.opacity(0.1), in: Capsule())
            Button("导出") {}
            Button(notesVisible ? "收起笔记" : "显示笔记") {
                notesVisible.toggle()
            }
        }
        .padding(.horizontal, 14)
        .frame(height: 48)
        .background(Color(nsColor: .windowBackgroundColor))
    }

    private var leftSidebar: some View {
        VStack(alignment: .leading, spacing: 0) {
            Picker("Sidebar", selection: .constant("books")) {
                Text("书籍").tag("books")
                Text("目录").tag("contents")
                Text("笔记").tag("notes")
            }
            .pickerStyle(.segmented)
            .padding(10)

            SidebarSection(title: "最近打开")
            SidebarRow(title: book.title, subtitle: "EPUB · 第 3 章", selected: true)
            SidebarRow(title: "创业维艰", subtitle: "EPUB · 未打开", selected: false)

            SidebarSection(title: "目录")
            SidebarRow(title: "第 1 章 心智阶梯", subtitle: nil, selected: false)
            SidebarRow(title: "第 3 章 定位不是口号", subtitle: nil, selected: true)
            SidebarRow(title: "第 4 章 选择战场", subtitle: nil, selected: false)

            Spacer()
        }
        .background(Color(nsColor: .controlBackgroundColor))
    }

    private var readerPane: some View {
        VStack(spacing: 0) {
            HStack {
                Text("第 3 章 · 42%")
                Spacer()
                Text("单击聚焦 · 双击备注 · 右键标红")
            }
            .font(.caption)
            .foregroundStyle(.secondary)
            .padding(.horizontal, 18)
            .frame(height: 34)
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("第 3 章 定位不是口号")
                        .font(.title2.bold())
                        .padding(.bottom, 6)
                    sentence(
                        "真正有效的定位，不是把产品说得更漂亮，而是在用户心智里找到一个可以被占据的位置。",
                        id: annotations[0].sentenceID,
                        hasNote: true,
                        highlighted: false
                    )
                    sentence(
                        "如果一个市场已经有清晰的第一名，后来者就不应该用同样的话术冲进去。",
                        id: annotations[1].sentenceID,
                        hasNote: false,
                        highlighted: true
                    )
                    sentence("更好的做法，是选择一个更小、更明确、用户已经有痛感的切口。", id: "s3")
                    sentence("这对读书软件也一样。它不应该先和 Apple Books 比书架、动画或云同步。", id: "s4")
                    sentence("它应该先把“读到一句话时马上能记录判断”这件事做到极顺。", id: "s5")
                }
                .font(.system(size: 17))
                .lineSpacing(8)
                .padding(44)
                .frame(maxWidth: 760, alignment: .leading)
                .background(.white, in: RoundedRectangle(cornerRadius: 8))
                .padding(48)
            }
            .background(Color(nsColor: .textBackgroundColor).opacity(0.35))
        }
    }

    private var notesRail: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("当前书笔记")
                    .font(.headline)
                Spacer()
                Button("›") { notesVisible = false }
            }
            .padding(.horizontal, 12)
            .frame(height: 48)
            Divider()
            HStack {
                Text("全部")
                Text("备注").foregroundStyle(.secondary)
                Text("标红").foregroundStyle(.secondary)
            }
            .font(.caption)
            .padding(10)
            Divider()
            ForEach(annotations, id: \.id) { annotation in
                Button {
                    selectedSentenceID = annotation.sentenceID
                } label: {
                    VStack(alignment: .leading, spacing: 5) {
                        Text(annotation.kind.rawValue)
                            .font(.caption)
                            .foregroundStyle(annotation.kind == .redHighlight ? .red : .orange)
                        Text(annotation.sourceText)
                            .font(.callout)
                            .lineLimit(2)
                        if let note = annotation.noteText {
                            Text(note)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .lineLimit(2)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(10)
                    .background(selectedSentenceID == annotation.sentenceID ? Color.blue.opacity(0.10) : Color.clear, in: RoundedRectangle(cornerRadius: 6))
                }
                .buttonStyle(.plain)
                .padding(.horizontal, 10)
                .padding(.top, 6)
            }
            Spacer()
        }
        .background(Color(nsColor: .controlBackgroundColor))
    }

    private func focusReaderEntry() {
        selectedSentenceID = annotations.first?.sentenceID
        notesVisible = true
        editorVisible = false
        draftNote = ""
    }

    private var selectedAnnotation: ReaderAnnotation? {
        annotations.first { $0.sentenceID == selectedSentenceID }
    }

    private func sentence(_ text: String, id: String, hasNote: Bool = false, highlighted: Bool = false) -> some View {
        Text(text + (hasNote ? " ●" : ""))
            .padding(.horizontal, 5)
            .padding(.vertical, 2)
            .background(background(for: id, highlighted: highlighted), in: RoundedRectangle(cornerRadius: 4))
            .overlay {
                if highlighted {
                    RoundedRectangle(cornerRadius: 4)
                        .stroke(.red.opacity(0.35), lineWidth: 1)
                }
            }
            .onTapGesture {
                selectedSentenceID = id
            }
            .onTapGesture(count: 2) {
                selectedSentenceID = id
                draftNote = selectedAnnotation?.noteText ?? ""
                editorVisible = true
            }
            .contextMenu {
                Button("切换红色标注") {}
                Button("添加/编辑备注") {
                    selectedSentenceID = id
                    draftNote = selectedAnnotation?.noteText ?? ""
                    editorVisible = true
                }
                Button("复制句子") {}
            }
    }

    private func background(for id: String, highlighted: Bool) -> Color {
        if highlighted {
            return .red.opacity(0.16)
        }
        if selectedSentenceID == id {
            return .blue.opacity(0.12)
        }
        return .clear
    }
}

private struct SidebarSection: View {
    let title: String

    var body: some View {
        Text(title)
            .font(.caption.bold())
            .foregroundStyle(.secondary)
            .padding(.horizontal, 14)
            .padding(.top, 14)
            .padding(.bottom, 6)
    }
}

private struct SidebarRow: View {
    let title: String
    let subtitle: String?
    let selected: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title)
                .lineLimit(1)
            if let subtitle {
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(8)
        .background(selected ? Color.blue.opacity(0.10) : Color.clear, in: RoundedRectangle(cornerRadius: 6))
        .padding(.horizontal, 10)
        .padding(.bottom, 4)
    }
}

private struct NoteEditorView: View {
    let sourceText: String
    @Binding var noteText: String
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("添加句子备注")
                .font(.headline)
            Text(sourceText)
                .font(.callout)
                .foregroundStyle(.secondary)
                .padding(10)
                .background(Color.blue.opacity(0.08), in: RoundedRectangle(cornerRadius: 6))
            TextEditor(text: $noteText)
                .font(.body)
                .border(Color(nsColor: .separatorColor))
            HStack {
                Spacer()
                Button("取消") { dismiss() }
                Button("保存") { dismiss() }
                    .keyboardShortcut(.return, modifiers: .command)
            }
        }
        .padding(18)
    }
}

private enum SampleData {
    static let book = BookReference(title: "好战略，坏战略", author: "理查德·鲁梅尔特", bookHash: "sample-good-strategy")
    static let now = Date(timeIntervalSince1970: 1_800_000_000)
    static let sentenceID = StableID.sentenceID(
        bookHash: book.bookHash,
        chapterLocator: "chapter-3",
        sentenceIndex: 1,
        sentenceText: "真正有效的定位，不是把产品说得更漂亮，而是在用户心智里找到一个可以被占据的位置。"
    )

    static let annotations: [ReaderAnnotation] = [
        ReaderAnnotation(
            id: StableID.annotationID(sentenceID: sentenceID, kind: .note),
            book: book,
            sentenceID: sentenceID,
            kind: .note,
            sourceText: "真正有效的定位，不是把产品说得更漂亮，而是在用户心智里找到一个可以被占据的位置。",
            noteText: "战略和定位都不是口号，而是选择一个能赢的位置。",
            color: nil,
            chapterTitle: "第 3 章 定位不是口号",
            chapterLocator: "chapter-3",
            rangeLocatorJSON: #"{"href":"chapter3.xhtml","locations":{"cfi":"/4/2/8"}}"#,
            createdAt: now,
            updatedAt: now
        ),
        ReaderAnnotation(
            id: "sample-red-highlight",
            book: book,
            sentenceID: "s2",
            kind: .redHighlight,
            sourceText: "如果一个市场已经有清晰的第一名，后来者就不应该用同样的话术冲进去。",
            noteText: nil,
            color: "red",
            chapterTitle: "第 3 章 定位不是口号",
            chapterLocator: "chapter-3",
            rangeLocatorJSON: #"{"href":"chapter3.xhtml","locations":{"cfi":"/4/2/10"}}"#,
            createdAt: now.addingTimeInterval(60),
            updatedAt: now.addingTimeInterval(60)
        )
    ]
}
