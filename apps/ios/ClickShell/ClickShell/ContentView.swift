import SwiftUI

struct ContentView: View {
    @StateObject private var store = ConnectionStore()
    @State private var didTrySavedConnection = false

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            if let baseURL = store.connectedBaseURL {
                ReaderShellView(store: store, baseURL: baseURL)
            } else {
                ConnectionView(store: store)
                    .task {
                        guard !didTrySavedConnection, store.hasSavedAddress else {
                            return
                        }
                        didTrySavedConnection = true
                        await store.connect()
                    }
            }
        }
    }
}
