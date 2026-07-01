import SwiftUI

struct ConnectionView: View {
    @ObservedObject var store: ConnectionStore

    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            Spacer(minLength: 24)

            VStack(alignment: .leading, spacing: 8) {
                Text("Click")
                    .font(.system(size: 42, weight: .bold))
                    .foregroundStyle(.white)
                Text("连接你的 Mac")
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.72))
            }

            VStack(alignment: .leading, spacing: 14) {
                Text("Mac 地址")
                    .font(.callout.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.7))
                TextField("<mac-lan-ip>", text: $store.hostInput)
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .textFieldStyle(.plain)
                    .padding(14)
                    .foregroundStyle(.white)
                    .background(Color.white.opacity(0.10), in: RoundedRectangle(cornerRadius: 8))

                Text("端口")
                    .font(.callout.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.7))
                TextField("18180", text: $store.portInput)
                    .keyboardType(.numberPad)
                    .textFieldStyle(.plain)
                    .padding(14)
                    .foregroundStyle(.white)
                    .background(Color.white.opacity(0.10), in: RoundedRectangle(cornerRadius: 8))
                    .frame(maxWidth: 180)

                Text("设备 token")
                    .font(.callout.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.7))
                TextField("approve 后的一次性 token", text: $store.accessTokenInput)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .textFieldStyle(.plain)
                    .padding(14)
                    .foregroundStyle(.white)
                    .background(Color.white.opacity(0.10), in: RoundedRectangle(cornerRadius: 8))

                Text("设备 ID：\(store.deviceID)")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.45))
            }

            Button {
                Task { await store.connect() }
            } label: {
                HStack {
                    if store.isChecking {
                        ProgressView()
                            .tint(.black)
                    }
                    Text(store.isChecking ? "连接中" : "连接")
                        .font(.headline)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
            }
            .buttonStyle(.plain)
            .foregroundStyle(.black)
            .background(Color.white, in: RoundedRectangle(cornerRadius: 8))
            .disabled(store.isChecking)

            if !store.statusMessage.isEmpty {
                Text(store.statusMessage)
                    .font(.callout)
                    .foregroundStyle(.white.opacity(0.72))
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 24)
        }
        .padding(.horizontal, 30)
        .frame(maxWidth: 520)
    }
}
