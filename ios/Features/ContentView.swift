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
                VStack(alignment: .leading, spacing: 24) {
                    readinessCard
                }
                .padding()
            }
            .navigationTitle("Today")
            .onAppear {
                viewModel.reloadSyncState()
                viewModel.loadTodayReadiness()

                if !observersConfigured {
                    HealthKitService.shared.enableObservers()
                    setupObservers()
                    observersConfigured = true
                }

                performInitialSync()
            }
        }
    }

    // MARK: - Main screen

    private var readinessCard: some View {
        Group {
            if let readiness = viewModel.todayReadiness {
                VStack(alignment: .leading, spacing: 16) {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Today")
                                .font(.headline)

                            Text(readiness.statusText ?? "No status")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }

                        Spacer()

                        Text(format(readiness.readinessScore))
                            .font(.system(size: 48, weight: .bold))
                            .foregroundStyle(readinessColor(readiness.readinessScore))
                    }

                    Text("Good day probability \(formatPercent(readiness.goodDayProbability))")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    HStack(spacing: 12) {
                        metricTile(
                            title: "Freshness",
                            value: freshnessText(from: readiness.explanation?.freshness)
                        )

                        metricTile(
                            title: "Recovery",
                            value: format(readiness.explanation?.recoveryScoreSimple)
                        )
                    }

                    if let recovery = readiness.explanation?.recoveryExplanation {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Recovery breakdown")
                                .font(.subheadline)
                                .fontWeight(.semibold)

                            scoreRow(title: "Sleep", score: recovery.sleepScore)
                            scoreRow(title: "HRV", score: recovery.hrvScore)
                            scoreRow(title: "Resting HR", score: recovery.rhrScore)
                        }
                    }

                    if readiness.explanation?.freshness == nil {
                        Text("Based only on recovery data")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding()
                .background(Color(.systemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color(.separator), lineWidth: 1)
                )
            } else if let error = viewModel.readinessErrorMessage {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Today")
                        .font(.headline)

                    Text("Failed to load readiness")
                        .font(.subheadline)

                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding()
                .background(Color(.systemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color(.separator), lineWidth: 1)
                )
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Today")
                        .font(.headline)

                    Text("No readiness data yet")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding()
                .background(Color(.systemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color(.separator), lineWidth: 1)
                )
            }
        }
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

    // MARK: - Sync actions

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
                    viewModel.loadTodayReadiness()
                }

            case .failure:
                break
            }
        }
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
                    viewModel.loadTodayReadiness()
                }

            case .failure:
                break
            }
        }
    }

    // MARK: - Reusable blocks

    @ViewBuilder
    private func metricTile(title: String, value: String) -> some View {
        VStack(spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)

            Text(value)
                .font(.headline)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    @ViewBuilder
    private func scoreRow(title: String, score: Double?) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(title)
                    .font(.subheadline)

                Spacer()

                Text(format(score))
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            ProgressView(value: (score ?? 0) / 100.0)
                .tint(readinessColor(score))
        }
    }

    // MARK: - Helpers

    private func format(_ value: Double?) -> String {
        guard let value else { return "n/a" }
        return String(format: "%.1f", value)
    }

    private func formatPercent(_ value: Double?) -> String {
        guard let value else { return "n/a" }
        return String(format: "%.1f%%", value * 100.0)
    }

    private func freshnessText(from value: Double?) -> String {
        guard let value else { return "No load data" }
        return String(format: "%.1f", value)
    }

    private func readinessColor(_ score: Double?) -> Color {
        guard let score else { return .gray }

        switch score {
        case ..<40:
            return .red
        case 40..<60:
            return .orange
        case 60..<75:
            return .yellow
        default:
            return .green
        }
    }
}

#Preview {
    ContentView()
}
