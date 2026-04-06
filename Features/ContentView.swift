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

    @State private var viewModel = ContentViewModel()

    // MARK: - Runtime control state

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
                viewModel.reloadSyncState()
                viewModel.refreshStatuses()

                if !observersConfigured {
                    HealthKitService.shared.enableObservers()
                    setupObservers()
                    observersConfigured = true
                }

                performInitialSync()
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
                Text("Status: \(viewModel.statusMessage)")

                if viewModel.isSyncInProgress {
                    ProgressView("Sync in progress...")
                }

                Button("Request permissions") {
                    viewModel.requestPermissions()
                }
                .buttonStyle(.borderedProminent)
                .disabled(viewModel.isSyncInProgress)

                Button("Refresh statuses") {
                    viewModel.refreshStatuses()
                }
                .buttonStyle(.bordered)
                .disabled(viewModel.isSyncInProgress)

                Button("Read sample data") {
                    readSampleData()
                }
                .buttonStyle(.bordered)
                .disabled(viewModel.isSyncInProgress)

                Button("Build JSON payload") {
                    buildPayloadPreview()
                }
                .buttonStyle(.bordered)
                .disabled(viewModel.isSyncInProgress)

                Button("Reset sync state") {
                    resetSyncState()
                }
                .buttonStyle(.bordered)
                .disabled(viewModel.isSyncInProgress)

                Button("Full sync") {
                    performFullSync()
                }
                .buttonStyle(.borderedProminent)
                .disabled(viewModel.isSyncInProgress)

                Button("Incremental sync") {
                    performIncrementalSync()
                }
                .buttonStyle(.bordered)
                .disabled(viewModel.isSyncInProgress)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var permissionsSection: some View {
        PermissionsSectionView(
            authorizationItems: viewModel.authorizationItems
        )
    }

    private var payloadSummarySection: some View {
        GroupBox("Payload summary") {
            if viewModel.payloadSummary.isEmpty {
                Text("No summary yet")
                    .foregroundStyle(.secondary)
            } else {
                Text(viewModel.payloadSummary)
                    .font(.system(.caption, design: .monospaced))
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    private var payloadPreviewSection: some View {
        PayloadPreviewSectionView(
            payloadPreview: viewModel.payloadPreview
        )
    }

    private var syncStateSection: some View {
        GroupBox("Sync state") {
            VStack(alignment: .leading, spacing: 8) {
                Text("Last successful sync: \(viewModel.syncState.lastSuccessfulSyncAt.map(DateFormatters.shortDateTime) ?? "None")")
                Text("Last payload generated: \(viewModel.syncState.lastPayloadGeneratedAt.map(DateFormatters.shortDateTime) ?? "None")")
                Text("Last sent item count: \(viewModel.syncState.lastSentItemCount)")
                Text("Last sync mode: \(viewModel.syncState.lastSyncMode?.rawValue ?? "None")")
                Text("Last error: \(viewModel.syncState.lastErrorMessage ?? "None")")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var weightSection: some View {
        WeightSectionView(
            samples: viewModel.weightSamples,
            formatDate: DateFormatters.shortDateTime
        )
    }

    private var restingHRSection: some View {
        RestingHRSectionView(
            samples: viewModel.restingHRSamples,
            formatDate: { DateFormatters.shortDateTime($0) }
        )
    }

    private var hrvSection: some View {
        HRVSectionView(
            samples: viewModel.hrvSamples,
            formatDate: { DateFormatters.shortDateTime($0) }
        )
    }

    private var sleepNightAggregatesSection: some View {
        SleepNightAggregatesSectionView(
            nights: viewModel.sleepNightAggregates,
            formatDate: { DateFormatters.shortDateTime($0) },
            formatDateOnly: { DateFormatters.mediumDate($0) }
        )
    }

    private var sleepSamplesSection: some View {
        SleepSamplesSectionView(
            samples: viewModel.sleepSamples,
            formatDate: { DateFormatters.shortDateTime($0) }
        )
    }

    // MARK: - Manual sample reading

    /// Ручное чтение примеров данных из HealthKit.
    /// Используется для быстрой визуальной проверки интеграции.
    private func readSampleData() {
        viewModel.readSampleData { result in
            switch result {
            case .success(let data):
                viewModel.weightSamples = data.weightSamples
                viewModel.restingHRSamples = data.restingHRSamples
                viewModel.hrvSamples = data.hrvSamples
                viewModel.sleepSamples = data.sleepSamples
                viewModel.sleepNightAggregates = data.sleepNightAggregates

            case .failure:
                // Ошибка уже обработана внутри viewModel.
                break
            }
        }
    }

    // MARK: - Sync actions

    /// Полный sync:
    /// перечитывает данные, строит полный payload и отправляет его на backend.
    private func performFullSync() {
        viewModel.performFullSync { result in
            switch result {
            case .success(let data):
                viewModel.weightSamples = data.weightSamples
                viewModel.restingHRSamples = data.restingHRSamples
                viewModel.hrvSamples = data.hrvSamples
                viewModel.sleepSamples = data.sleepSamples
                viewModel.sleepNightAggregates = data.sleepNightAggregates

                viewModel.sendPayload(data.payload, mode: .full) {
                    viewModel.isSyncInProgress = false
                }

            case .failure:
                // Ошибка уже обработана внутри viewModel.
                break
            }
        }
    }

    /// Incremental sync:
    /// использует anchors и отправляет только delta payload.
    private func performIncrementalSync() {
        viewModel.performIncrementalSync { result in
            switch result {
            case .success(let data):
                guard let payload = data.payload else {
                    return
                }

                viewModel.newHRVSamples = data.newHRVSamples
                viewModel.newRestingHRSamples = data.newRestingHRSamples
                viewModel.newSleepNightAggregates = data.newSleepNightAggregates

                if !data.newHRVSamples.isEmpty {
                    viewModel.hrvSamples = data.newHRVSamples
                }

                if !data.newRestingHRSamples.isEmpty {
                    viewModel.restingHRSamples = data.newRestingHRSamples
                }

                if !data.newSleepNightAggregates.isEmpty {
                    viewModel.sleepNightAggregates = data.newSleepNightAggregates
                }

                viewModel.sendPayload(payload, mode: .incremental) {
                    viewModel.isSyncInProgress = false
                }

            case .failure:
                // Ошибка уже обработана внутри viewModel.
                break
            }
        }
    }

    /// Сбрасывает локальное sync state.
    private func resetSyncState() {
        viewModel.resetSyncState()
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
            guard !viewModel.isSyncInProgress else { return }

            viewModel.statusMessage = "Auto sync triggered: \(reason)"
            performIncrementalSync()
        }

        pendingAutoSyncWorkItem = workItem
        viewModel.statusMessage = "Auto sync scheduled: \(reason)"

        DispatchQueue.main.asyncAfter(deadline: .now() + 5, execute: workItem)
    }

    // MARK: - Helpers

    private func buildPayloadPreview() {
        let payload = HealthKitService.shared.buildHealthSyncPayload(
            sleepAggregates: viewModel.sleepNightAggregates,
            restingHRSamples: viewModel.restingHRSamples,
            hrvSamples: viewModel.hrvSamples,
            weightSamples: viewModel.weightSamples
        )

        viewModel.buildPayloadPreview(from: payload)
    }
    
    private func performInitialSync() {
        viewModel.performInitialSyncIfNeeded { result in
            switch result {
            case .success(let data):
                guard let payload = data.payload else { return }

                if !data.newHRVSamples.isEmpty {
                    viewModel.hrvSamples = data.newHRVSamples
                }

                if !data.newRestingHRSamples.isEmpty {
                    viewModel.restingHRSamples = data.newRestingHRSamples
                }

                if !data.newSleepNightAggregates.isEmpty {
                    viewModel.sleepNightAggregates = data.newSleepNightAggregates
                }

                viewModel.sendPayload(payload, mode: .incremental) {
                    viewModel.isSyncInProgress = false
                }

            case .failure:
                break
            }
        }
    }
}

#Preview {
    ContentView()
}
