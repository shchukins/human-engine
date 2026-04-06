//
//  ContentView.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 05.04.2026.
//

import SwiftUI
import HealthKit

struct ContentView: View {

    // MARK: - UI state

    @State private var statusMessage = "Not requested"
    @State private var authorizationItems: [(name: String, status: String)] = []

    // MARK: - Loaded HealthKit data

    @State private var weightSamples: [WeightSample] = []
    @State private var restingHRSamples: [RestingHRSample] = []
    @State private var hrvSamples: [HRVSample] = []
    @State private var sleepSamples: [SleepSample] = []
    @State private var sleepNightAggregates: [SleepNightAggregate] = []

    // MARK: - Incremental / delta data

    @State private var newHRVSamples: [HRVSample] = []
    @State private var newRestingHRSamples: [RestingHRSample] = []
    @State private var newSleepNightAggregates: [SleepNightAggregate] = []

    // MARK: - Payload / sync state

    @State private var payloadPreview: String = ""
    @State private var payloadSummary: String = ""
    @State private var syncState = SyncStateStore.shared.load()

    // MARK: - Runtime control state

    @State private var isSyncInProgress = false
    @State private var observersConfigured = false
    @State private var pendingAutoSyncWorkItem: DispatchWorkItem?

    // MARK: - View

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    headerSection
                    actionsSection
                    permissionsSection
                    payloadSummarySection
                    payloadPreviewSection
                    syncStateSection
                    weightSection
                    restingHRSection
                    hrvSection
                    sleepNightAggregatesSection
                    sleepSamplesSection
                }
                .padding()
            }
            .navigationTitle("HealthKit")
            .onAppear {
                syncState = SyncStateStore.shared.load()
                refreshStatuses()

                // Подключаем observers только один раз за жизненный цикл view.
                if !observersConfigured {
                    HealthKitService.shared.enableObservers()
                    setupObservers()
                    observersConfigured = true
                }
            }
        }
    }

    // MARK: - Sections

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Human Engine")
                .font(.largeTitle)
                .bold()

            Text("HealthKit integration MVP")
                .font(.headline)
                .foregroundStyle(.secondary)
        }
    }

    private var actionsSection: some View {
        GroupBox("Authorization & Sync") {
            VStack(alignment: .leading, spacing: 12) {
                Text("Status: \(statusMessage)")

                if isSyncInProgress {
                    ProgressView("Sync in progress...")
                }

                Button("Request permissions") {
                    requestPermissions()
                }
                .buttonStyle(.borderedProminent)
                .disabled(isSyncInProgress)

                Button("Refresh statuses") {
                    refreshStatuses()
                }
                .buttonStyle(.bordered)
                .disabled(isSyncInProgress)

                Button("Read sample data") {
                    readSampleData()
                }
                .buttonStyle(.bordered)
                .disabled(isSyncInProgress)

                Button("Build JSON payload") {
                    buildPayloadPreview()
                }
                .buttonStyle(.bordered)
                .disabled(isSyncInProgress)

                Button("Reset sync state") {
                    resetSyncState()
                }
                .buttonStyle(.bordered)
                .disabled(isSyncInProgress)

                Button("Full sync") {
                    performFullSync()
                }
                .buttonStyle(.borderedProminent)
                .disabled(isSyncInProgress)

                Button("Incremental sync") {
                    performIncrementalSync()
                }
                .buttonStyle(.bordered)
                .disabled(isSyncInProgress)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var permissionsSection: some View {
        GroupBox("Permissions") {
            if authorizationItems.isEmpty {
                Text("No data yet")
                    .foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(authorizationItems, id: \.name) { item in
                        HStack {
                            Text(item.name)
                            Spacer()
                            Text(item.status)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
        }
    }

    private var payloadSummarySection: some View {
        GroupBox("Payload summary") {
            if payloadSummary.isEmpty {
                Text("No summary yet")
                    .foregroundStyle(.secondary)
            } else {
                Text(payloadSummary)
                    .font(.system(.caption, design: .monospaced))
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    private var payloadPreviewSection: some View {
        GroupBox("Payload preview") {
            if payloadPreview.isEmpty {
                Text("No payload yet")
                    .foregroundStyle(.secondary)
            } else {
                ScrollView(.horizontal) {
                    Text(payloadPreview)
                        .font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    private var syncStateSection: some View {
        GroupBox("Sync state") {
            VStack(alignment: .leading, spacing: 8) {
                Text("Last successful sync: \(syncState.lastSuccessfulSyncAt.map(formatDate) ?? "None")")
                Text("Last payload generated: \(syncState.lastPayloadGeneratedAt.map(formatDate) ?? "None")")
                Text("Last sent item count: \(syncState.lastSentItemCount)")
                Text("Last sync mode: \(syncState.lastSyncMode?.rawValue ?? "None")")
                Text("Last error: \(syncState.lastErrorMessage ?? "None")")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var weightSection: some View {
        GroupBox("Weight samples") {
            if weightSamples.isEmpty {
                Text("No weight samples")
                    .foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(weightSamples.prefix(5)) { sample in
                        Text("\(formatDate(sample.date))  •  \(sample.kilograms, specifier: "%.1f") kg")
                    }
                }
            }
        }
    }

    private var restingHRSection: some View {
        GroupBox("Resting HR samples") {
            if restingHRSamples.isEmpty {
                Text("No resting HR samples")
                    .foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(restingHRSamples.prefix(5)) { sample in
                        Text("\(formatDate(sample.date))  •  \(sample.bpm, specifier: "%.0f") bpm")
                    }
                }
            }
        }
    }

    private var hrvSection: some View {
        GroupBox("HRV samples") {
            if hrvSamples.isEmpty {
                Text("No HRV samples")
                    .foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(hrvSamples.prefix(5)) { sample in
                        Text("\(formatDate(sample.date))  •  \(sample.milliseconds, specifier: "%.1f") ms")
                    }
                }
            }
        }
    }

    private var sleepNightAggregatesSection: some View {
        GroupBox("Sleep night aggregates") {
            if sleepNightAggregates.isEmpty {
                Text("No sleep aggregates")
                    .foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 12) {
                    ForEach(sleepNightAggregates.prefix(5)) { night in
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Wake date: \(formatDateOnly(night.wakeDate))")
                                .font(.headline)

                            Text("Sleep: \(night.totalSleepMinutes, specifier: "%.0f") min")
                            Text("Awake: \(night.awakeMinutes, specifier: "%.0f") min")
                            Text("Core: \(night.coreMinutes, specifier: "%.0f") min")
                            Text("REM: \(night.remMinutes, specifier: "%.0f") min")
                            Text("Deep: \(night.deepMinutes, specifier: "%.0f") min")
                            Text("In Bed: \(night.inBedMinutes, specifier: "%.0f") min")

                            Text("\(formatDate(night.sleepStart)) → \(formatDate(night.sleepEnd))")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
        }
    }

    private var sleepSamplesSection: some View {
        GroupBox("Sleep samples") {
            if sleepSamples.isEmpty {
                Text("No sleep samples")
                    .foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(sleepSamples.prefix(10)) { sample in
                        VStack(alignment: .leading, spacing: 2) {
                            Text("\(sample.stage)  •  \(sample.durationMinutes, specifier: "%.0f") min")
                            Text("\(formatDate(sample.startDate)) → \(formatDate(sample.endDate))")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
        }
    }

    // MARK: - Permissions

    /// Запрашивает доступ к нужным типам HealthKit.
    private func requestPermissions() {
        HealthKitService.shared.requestAuthorization { result in
            switch result {
            case .success:
                statusMessage = "Authorization successful"
                refreshStatuses()

            case .failure(let error):
                statusMessage = error.localizedDescription
                refreshStatuses()
            }
        }
    }

    /// Обновляет статусы разрешений по HealthKit типам.
    private func refreshStatuses() {
        let statuses = HealthKitService.shared.authorizationStatuses()

        authorizationItems = statuses
            .map { key, value in
                (name: key, status: mapAuthorizationStatus(value))
            }
            .sorted { $0.name < $1.name }
    }

    // MARK: - Manual sample reading

    /// Ручное чтение примеров данных из HealthKit.
    /// Используется для быстрой визуальной проверки интеграции.
    private func readSampleData() {
        statusMessage = "Reading sample data..."

        HealthKitService.shared.fetchLatestWeightSample { result in
            switch result {
            case .success(let weights):
                weightSamples = weights
            case .failure(let error):
                statusMessage = "Weight read error: \(error.localizedDescription)"
            }
        }

        HealthKitService.shared.fetchRestingHRSamplesForLast7Days { result in
            switch result {
            case .success(let restingHR):
                restingHRSamples = restingHR
            case .failure(let error):
                statusMessage = "Resting HR read error: \(error.localizedDescription)"
            }
        }

        HealthKitService.shared.fetchHRVSamplesForLast7Days { result in
            switch result {
            case .success(let hrv):
                hrvSamples = hrv
            case .failure(let error):
                statusMessage = "HRV read error: \(error.localizedDescription)"
            }
        }

        HealthKitService.shared.fetchSleepSamplesForLast7Days { result in
            switch result {
            case .success(let sleep):
                sleepSamples = sleep
                sleepNightAggregates = HealthKitService.shared.buildSleepNightAggregates(from: sleep)
                statusMessage = "Sample data loaded"
            case .failure(let error):
                statusMessage = "Sleep read error: \(error.localizedDescription)"
            }
        }
    }

    // MARK: - Payload building

    /// Строит полный payload и показывает:
    /// 1. краткую сводку
    /// 2. обрезанный JSON preview
    private func buildPayloadPreview() {
        let payload = HealthKitService.shared.buildHealthSyncPayload(
            sleepAggregates: sleepNightAggregates,
            restingHRSamples: restingHRSamples,
            hrvSamples: hrvSamples,
            weightSamples: weightSamples
        )

        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]

        do {
            let data = try encoder.encode(payload)
            let fullText = String(data: data, encoding: .utf8) ?? "Failed to render payload"

            // Ограничиваем размер preview, чтобы UI не зависал на больших payload.
            let previewLimit = 4000
            if fullText.count > previewLimit {
                payloadPreview = String(fullText.prefix(previewLimit)) + "\n\n... truncated ..."
            } else {
                payloadPreview = fullText
            }

            updatePayloadSummary(from: payload)
            statusMessage = "Payload preview built"

            syncState.lastPayloadGeneratedAt = Date()
            syncState.lastErrorMessage = nil
            syncState.lastSentItemCount = payloadItemCount(payload)
            SyncStateStore.shared.save(syncState)

        } catch {
            payloadPreview = ""
            statusMessage = "Payload build error: \(error.localizedDescription)"
            syncState.lastErrorMessage = error.localizedDescription
            SyncStateStore.shared.save(syncState)
        }
    }

    /// Обновляет только краткую сводку payload из текущего полного состояния.
    private func updatePayloadSummaryOnly() {
        let payload = HealthKitService.shared.buildHealthSyncPayload(
            sleepAggregates: sleepNightAggregates,
            restingHRSamples: restingHRSamples,
            hrvSamples: hrvSamples,
            weightSamples: weightSamples
        )

        updatePayloadSummary(from: payload)
    }

    /// Формирует краткую summary по уже готовому payload.
    private func updatePayloadSummary(from payload: HealthSyncPayload) {
        let encoder = JSONEncoder()

        do {
            let data = try encoder.encode(payload)
            let itemCount = payloadItemCount(payload)

            if itemCount == 0 {
                payloadSummary = """
No incremental payload data
payloadSizeBytes: \(data.count)
"""
                return
            }

            payloadSummary = """
sleepNights: \(payload.sleepNights.count)
restingHeartRateDaily: \(payload.restingHeartRateDaily.count)
hrvSamples: \(payload.hrvSamples.count)
latestWeight: \(payload.latestWeight == nil ? 0 : 1)
payloadSizeBytes: \(data.count)
"""
        } catch {
            payloadSummary = "Failed to build payload summary"
        }
    }

    // MARK: - Sync actions

    /// Полный sync:
    /// перечитывает данные, строит полный payload и отправляет его на backend.
    private func performFullSync() {
        guard !isSyncInProgress else { return }

        isSyncInProgress = true
        statusMessage = "Running full sync..."

        SyncService.shared.performFullSync { result in
            switch result {
            case .success(let data):
                weightSamples = data.weightSamples
                restingHRSamples = data.restingHRSamples
                hrvSamples = data.hrvSamples
                sleepSamples = data.sleepSamples
                sleepNightAggregates = data.sleepNightAggregates

                updatePayloadSummary(from: data.payload)
                sendPayload(data.payload, mode: .full)

            case .failure(let error):
                statusMessage = "Full sync error: \(error.localizedDescription)"
                syncState.lastErrorMessage = error.localizedDescription
                SyncStateStore.shared.save(syncState)
                isSyncInProgress = false
            }
        }
    }

    /// Incremental sync:
    /// использует anchors и отправляет только delta payload.
    private func performIncrementalSync() {
        guard !isSyncInProgress else { return }

        isSyncInProgress = true
        statusMessage = "Running incremental sync..."

        SyncService.shared.performIncrementalSync { result in
            switch result {
            case .success(let data):
                guard let payload = data.payload else {
                    updatePayloadSummary(from: HealthSyncPayload(
                        generatedAt: ISO8601DateFormatter().string(from: Date()),
                        timezone: TimeZone.current.identifier,
                        sleepNights: [],
                        restingHeartRateDaily: [],
                        hrvSamples: [],
                        latestWeight: nil
                    ))

                    statusMessage = "Incremental sync: no new data"
                    syncState.lastErrorMessage = nil
                    syncState.lastSyncMode = .incremental
                    SyncStateStore.shared.save(syncState)
                    isSyncInProgress = false
                    return
                }

                newHRVSamples = data.newHRVSamples
                newRestingHRSamples = data.newRestingHRSamples
                newSleepNightAggregates = data.newSleepNightAggregates

                if !data.newHRVSamples.isEmpty {
                    hrvSamples = data.newHRVSamples
                }

                if !data.newRestingHRSamples.isEmpty {
                    restingHRSamples = data.newRestingHRSamples
                }

                if !data.newSleepNightAggregates.isEmpty {
                    sleepNightAggregates = data.newSleepNightAggregates
                }

                updatePayloadSummary(from: payload)
                sendPayload(payload, mode: .incremental)

            case .failure(let error):
                statusMessage = "Incremental sync error: \(error.localizedDescription)"
                syncState.lastErrorMessage = error.localizedDescription
                SyncStateStore.shared.save(syncState)
                isSyncInProgress = false
            }
        }
    }

    /// Общая отправка уже готового payload на backend.
    private func sendPayload(_ payload: HealthSyncPayload, mode: SyncMode) {
        statusMessage = "Sending..."

        let itemCount = payloadItemCount(payload)

        SyncService.shared.sendPayload(payload) { result in
            switch result {
            case .success:
                statusMessage = mode == .full ? "Full sync sent" : "Incremental sent"
                syncState.lastSuccessfulSyncAt = Date()
                syncState.lastPayloadGeneratedAt = Date()
                syncState.lastErrorMessage = nil
                syncState.lastSentItemCount = itemCount
                syncState.lastSyncMode = mode
                SyncStateStore.shared.save(syncState)

            case .failure(let error):
                statusMessage = "Send error: \(error.localizedDescription)"
                syncState.lastPayloadGeneratedAt = Date()
                syncState.lastErrorMessage = error.localizedDescription
                SyncStateStore.shared.save(syncState)
            }

            isSyncInProgress = false
        }
    }

    /// Сбрасывает локальное sync state.
    private func resetSyncState() {
        syncState = .empty
        SyncStateStore.shared.clear()
        statusMessage = "Sync state reset"
    }

    // MARK: - Auto sync / observers

    /// Подписка на локальные уведомления, которые публикует HealthKitService
    /// при обновлении соответствующих типов данных.
    private func setupObservers() {
        NotificationCenter.default.addObserver(
            forName: .healthKitHRVUpdated,
            object: nil,
            queue: .main
        ) { _ in
            triggerAutoSync(reason: "HRV updated")
        }

        NotificationCenter.default.addObserver(
            forName: .healthKitRestingHRUpdated,
            object: nil,
            queue: .main
        ) { _ in
            triggerAutoSync(reason: "Resting HR updated")
        }

        NotificationCenter.default.addObserver(
            forName: .healthKitSleepUpdated,
            object: nil,
            queue: .main
        ) { _ in
            triggerAutoSync(reason: "Sleep updated")
        }
    }

    /// Debounce для auto sync:
    /// если несколько сигналов приходят подряд, выполняем только один sync.
    private func triggerAutoSync(reason: String) {
        pendingAutoSyncWorkItem?.cancel()

        let workItem = DispatchWorkItem {
            guard !isSyncInProgress else { return }

            statusMessage = "Auto sync triggered: \(reason)"
            performIncrementalSync()
        }

        pendingAutoSyncWorkItem = workItem
        statusMessage = "Auto sync scheduled: \(reason)"

        DispatchQueue.main.asyncAfter(deadline: .now() + 5, execute: workItem)
    }

    // MARK: - Helpers

    private func payloadItemCount(_ payload: HealthSyncPayload) -> Int {
        payload.sleepNights.count +
        payload.restingHeartRateDaily.count +
        payload.hrvSamples.count +
        (payload.latestWeight == nil ? 0 : 1)
    }

    private func mapAuthorizationStatus(_ status: HKAuthorizationStatus) -> String {
        switch status {
        case .notDetermined:
            return "Not determined"
        case .sharingDenied:
            return "Denied"
        case .sharingAuthorized:
            return "Authorized"
        @unknown default:
            return "Unknown"
        }
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }

    private func formatDateOnly(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        return formatter.string(from: date)
    }
}

#Preview {
    ContentView()
}
