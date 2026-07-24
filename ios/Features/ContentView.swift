import SwiftUI

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase
    @State private var viewModel = ContentViewModel()

    private let actionColumns = [
        GridItem(.flexible(), spacing: 12),
        GridItem(.flexible(), spacing: 12)
    ]

    var body: some View {
        NavigationStack {
            ZStack {
                HEColor.background
                    .ignoresSafeArea()

                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        topBar
                        decisionCard
                        if viewModel.requiresHealthKitAuthorization {
                            healthKitAccessCard
                        }
                        recoverySignalsCard
                        dataFreshnessCard
                        syncDataCard
                        diagnosticsEntry
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 16)
                    .padding(.bottom, 28)
                }
            }
            .toolbar(.hidden, for: .navigationBar)
            .onAppear {
                viewModel.prepareDashboardForDisplay {
                    if scenePhase == .active {
                        viewModel.triggerAutoSync(reason: "app_open")
                    }
                }
            }
            .onChange(of: scenePhase) { _, newPhase in
                guard newPhase == .active else { return }
                viewModel.triggerAutoSync(reason: "app_active")
            }
            .onReceive(NotificationCenter.default.publisher(for: .syncStateDidChange)) { _ in
                viewModel.reloadSyncState()
                viewModel.refreshStatuses()
            }
            .onReceive(NotificationCenter.default.publisher(for: .autoSyncDidFinish)) { _ in
                viewModel.reloadSyncState()
                viewModel.refreshStatuses()
            }
        }
    }

    private var topBar: some View {
        HStack(alignment: .top, spacing: 16) {
            VStack(alignment: .leading, spacing: 3) {
                Text("WHATTE")
                    .font(.system(size: 34, weight: .black, design: .default))
                    .foregroundStyle(HEColor.primaryText)
                    .lineLimit(1)
                    .accessibilityAddTraits(.isHeader)

                Text("WHAT NOW?")
                    .font(.system(size: 16, weight: .semibold, design: .default))
                    .foregroundStyle(HEColor.accentGreen)
                    .lineLimit(1)

                Text("Decision engine for training")
                    .font(HETypography.body)
                    .foregroundStyle(HEColor.secondaryText)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
            }

            Spacer()

            NavigationLink {
                DebugView()
            } label: {
                Image(systemName: "gearshape")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(HEColor.secondaryText)
                    .frame(width: 44, height: 44)
                    .background(HEColor.card)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .stroke(HEColor.border, lineWidth: 1)
                    )
            }
            .accessibilityLabel("Diagnostics")
        }
    }

    private var decisionCard: some View {
        DashboardCard(title: "WHAT NOW?", accent: HEColor.accentGreen) {
            VStack(alignment: .leading, spacing: 14) {
                Text(viewModel.decisionStatusText)
                    .font(HETypography.status)
                    .foregroundStyle(HEColor.primaryText)
                    .lineLimit(3)
                    .minimumScaleFactor(0.72)
                    .fixedSize(horizontal: false, vertical: true)

                Text(viewModel.decisionSupportingText)
                    .font(HETypography.body)
                    .foregroundStyle(HEColor.secondaryText)
                    .fixedSize(horizontal: false, vertical: true)

                HStack(spacing: 10) {
                    StatusBadge(text: viewModel.compactFreshnessStatusText, color: freshnessStatusColor)
                    StatusBadge(text: viewModel.backendStatusLabel.capitalized, color: color(forStatusKey: viewModel.backendStatusColor))
                }
            }
        }
    }

    private var healthKitAccessCard: some View {
        DashboardCard(title: "HEALTHKIT ACCESS REQUIRED", accent: HEColor.accentYellow) {
            VStack(alignment: .leading, spacing: 14) {
                Text("HealthKit access required")
                    .font(HETypography.title)
                    .foregroundStyle(HEColor.primaryText)
                    .fixedSize(horizontal: false, vertical: true)

                Text("Enable Sleep, HRV, Resting HR, and Weight access to show your latest signals.")
                    .font(HETypography.body)
                    .foregroundStyle(HEColor.secondaryText)
                    .fixedSize(horizontal: false, vertical: true)

                Button("Enable HealthKit") {
                    viewModel.requestPermissions()
                }
                .buttonStyle(.borderedProminent)
                .tint(HEColor.accentGreen)
            }
        }
    }

    private var recoverySignalsCard: some View {
        DashboardCard(title: "RECOVERY SIGNALS", accent: HEColor.accentCyan) {
            VStack(alignment: .leading, spacing: 16) {
                Text("Latest known HealthKit signals")
                    .font(HETypography.body)
                    .foregroundStyle(HEColor.secondaryText)

                LazyVGrid(columns: actionColumns, alignment: .leading, spacing: 14) {
                    recoverySignalMetric(
                        title: "SLEEP",
                        value: viewModel.latestSleepValue,
                        time: viewModel.latestSleepTimeText,
                        color: HEColor.accentGreen
                    )
                    recoverySignalMetric(
                        title: "HRV",
                        value: viewModel.latestHRVValue,
                        time: viewModel.latestHRVTimeText,
                        color: HEColor.accentCyan
                    )
                    recoverySignalMetric(
                        title: "RESTING HR",
                        value: viewModel.latestRestingHRValue,
                        time: viewModel.latestRestingHRTimeText,
                        color: HEColor.accentYellow
                    )
                    recoverySignalMetric(
                        title: "WEIGHT",
                        value: viewModel.latestWeightValue,
                        time: viewModel.latestWeightTimeText,
                        color: HEColor.primaryText
                    )
                }
            }
        }
    }

    private var dataFreshnessCard: some View {
        DashboardCard(title: "DATA FRESHNESS", accent: HEColor.accentGreen, secondaryBackground: true) {
            VStack(alignment: .leading, spacing: 14) {
                HStack(spacing: 10) {
                    StatusBadge(text: viewModel.compactFreshnessStatusText, color: freshnessStatusColor)

                    if viewModel.isSyncInProgress {
                        ProgressView()
                            .tint(HEColor.accentGreen)
                    }
                }

                ViewThatFits {
                    HStack(alignment: .top, spacing: 12) {
                        freshnessMetric(title: "Last successful sync", value: viewModel.lastSyncDisplayText)
                        freshnessMetric(title: "Last sync attempt", value: viewModel.lastSyncAttemptDisplayText)
                    }

                    VStack(alignment: .leading, spacing: 12) {
                        freshnessMetric(title: "Last successful sync", value: viewModel.lastSyncDisplayText)
                        freshnessMetric(title: "Last sync attempt", value: viewModel.lastSyncAttemptDisplayText)
                    }
                }

                ViewThatFits {
                    HStack(alignment: .top, spacing: 12) {
                        freshnessMetric(
                            title: "Sync mode",
                            value: viewModel.lastSyncModeDisplayText,
                            valueColor: accentColor(forMode: viewModel.syncState.lastSyncMode)
                        )
                        freshnessMetric(title: "Items sent", value: "\(viewModel.syncState.lastSentItemCount)")
                    }

                    VStack(alignment: .leading, spacing: 12) {
                        freshnessMetric(
                            title: "Sync mode",
                            value: viewModel.lastSyncModeDisplayText,
                            valueColor: accentColor(forMode: viewModel.syncState.lastSyncMode)
                        )
                        freshnessMetric(title: "Items sent", value: "\(viewModel.syncState.lastSentItemCount)")
                    }
                }

                ViewThatFits {
                    HStack(alignment: .top, spacing: 12) {
                        freshnessMetric(title: "Backend status", value: viewModel.backendStatusLabel.capitalized, valueColor: color(forStatusKey: viewModel.backendStatusColor))
                        freshnessMetric(
                            title: "Auto sync",
                            value: viewModel.autoSyncDisplayText,
                            valueColor: viewModel.syncState.hasPendingAutoSync ? HEColor.accentYellow : HEColor.primaryText
                        )
                    }

                    VStack(alignment: .leading, spacing: 12) {
                        freshnessMetric(title: "Backend status", value: viewModel.backendStatusLabel.capitalized, valueColor: color(forStatusKey: viewModel.backendStatusColor))
                        freshnessMetric(
                            title: "Auto sync",
                            value: viewModel.autoSyncDisplayText,
                            valueColor: viewModel.syncState.hasPendingAutoSync ? HEColor.accentYellow : HEColor.primaryText
                        )
                    }
                }

                if let error = viewModel.syncState.lastErrorMessage, !error.isEmpty {
                    Divider()
                        .overlay(HEColor.border)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Last error")
                            .font(HETypography.overline)
                            .foregroundStyle(HEColor.error)

                        Text(error)
                            .font(.caption)
                            .foregroundStyle(HEColor.secondaryText)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        }
    }

    private var syncDataCard: some View {
        DashboardCard(title: "SYNC", accent: HEColor.accentGreen, secondaryBackground: true) {
            VStack(alignment: .leading, spacing: 14) {
                Button {
                    viewModel.runSmartSyncFromMainScreen()
                } label: {
                    HStack(spacing: 12) {
                        Image(systemName: "arrow.clockwise")
                            .font(.system(size: 17, weight: .semibold))

                        VStack(alignment: .leading, spacing: 2) {
                            Text("Sync now")
                                .font(.system(size: 16, weight: .semibold, design: .default))

                            Text(viewModel.manualSyncSubtitle)
                                .font(.caption)
                        }
                        .lineLimit(2)

                        Spacer()
                    }
                    .frame(minHeight: 44)
                }
                .disabled(viewModel.isSyncInProgress)
                .buttonStyle(.borderedProminent)
                .tint(HEColor.accentGreen)
                .foregroundStyle(HEColor.background)

                if viewModel.isSyncInProgress {
                    ProgressView("Sync in progress...")
                        .tint(HEColor.accentGreen)
                        .foregroundStyle(HEColor.secondaryText)
                }

                Text("Full sync runs automatically until the first successful sync. Incremental sync is used after that.")
                    .font(.caption)
                    .foregroundStyle(HEColor.secondaryText)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var diagnosticsEntry: some View {
        DashboardCard(title: "DIAGNOSTICS", accent: HEColor.accentCyan, secondaryBackground: true) {
            VStack(alignment: .leading, spacing: 14) {
                Text("Technical sync tools, HealthKit read checks, payload preview, and backend configuration.")
                    .font(HETypography.body)
                    .foregroundStyle(HEColor.secondaryText)
                    .fixedSize(horizontal: false, vertical: true)

                NavigationLink {
                    DebugView()
                } label: {
                    HStack {
                        Text("Open diagnostics")
                            .font(.system(size: 16, weight: .semibold, design: .default))
                            .foregroundStyle(HEColor.primaryText)

                        Spacer()

                        Image(systemName: "chevron.right")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(HEColor.secondaryText)
                    }
                    .frame(minHeight: 44)
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func recoverySignalMetric(title: String, value: String, time: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(HETypography.overline)
                .foregroundStyle(HEColor.secondaryText)
                .tracking(1.0)
                .lineLimit(1)

            Text(value)
                .font(.system(size: 26, weight: .semibold, design: .default))
                .monospacedDigit()
                .foregroundStyle(color)
                .lineLimit(1)
                .minimumScaleFactor(0.7)

            Text(time)
                .font(.caption2.monospacedDigit())
                .foregroundStyle(HEColor.secondaryText)
                .lineLimit(1)
                .minimumScaleFactor(0.75)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(HEColor.cardSecondary)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(HEColor.border, lineWidth: 1)
        )
    }

    private func freshnessMetric(title: String, value: String, valueColor: Color = HEColor.primaryText) -> some View {
        MetricRow(title: title, value: value, valueColor: valueColor)
            .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func color(forStatusKey key: String) -> Color {
        switch key {
        case "connected":
            return HEColor.accentGreen
        case "warning":
            return HEColor.accentYellow
        case "error":
            return HEColor.error
        default:
            return HEColor.accentCyan
        }
    }

    private func accentColor(forMode mode: SyncMode?) -> Color {
        switch mode {
        case .full:
            return HEColor.accentGreen
        case .incremental:
            return HEColor.accentCyan
        case .backfill:
            return HEColor.accentYellow
        case nil:
            return HEColor.secondaryText
        }
    }

    private var freshnessStatusColor: Color {
        if viewModel.requiresHealthKitAuthorization {
            return HEColor.accentYellow
        }

        if viewModel.syncState.lastErrorMessage != nil {
            return HEColor.error
        }

        if viewModel.isSyncInProgress {
            return HEColor.accentCyan
        }

        return HEColor.accentGreen
    }
}

#Preview {
    ContentView()
}
