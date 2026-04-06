//
//  ContentViewModel.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 06.04.2026.
//

import Foundation
import HealthKit
import Observation

@Observable
final class ContentViewModel {

    
    struct SampleReadResult {
        let weightSamples: [WeightSample]
        let restingHRSamples: [RestingHRSample]
        let hrvSamples: [HRVSample]
        let sleepSamples: [SleepSample]
        let sleepNightAggregates: [SleepNightAggregate]
    }
    
    // MARK: - Loaded HealthKit data

    var weightSamples: [WeightSample] = []
    var restingHRSamples: [RestingHRSample] = []
    var hrvSamples: [HRVSample] = []
    var sleepSamples: [SleepSample] = []
    var sleepNightAggregates: [SleepNightAggregate] = []

    // MARK: - Incremental / delta data

    var newHRVSamples: [HRVSample] = []
    var newRestingHRSamples: [RestingHRSample] = []
    var newSleepNightAggregates: [SleepNightAggregate] = []
    
    // MARK: - UI state

    var statusMessage: String = "Not requested"
    var authorizationItems: [(name: String, status: String)] = []
    var payloadPreview: String = ""
    var payloadSummary: String = ""
    var syncState: SyncState = SyncStateStore.shared.load()
    var isSyncInProgress: Bool = false

    // MARK: - Permissions

    func requestPermissions() {
        HealthKitService.shared.requestAuthorization { [weak self] result in
            guard let self else { return }

            switch result {
            case .success:
                self.statusMessage = "Authorization successful"
                self.refreshStatuses()

            case .failure(let error):
                self.statusMessage = error.localizedDescription
                self.refreshStatuses()
            }
        }
    }

    func refreshStatuses() {
        let statuses = HealthKitService.shared.authorizationStatuses()

        authorizationItems = statuses
            .map { key, value in
                (name: key, status: Self.mapAuthorizationStatus(value))
            }
            .sorted { $0.name < $1.name }
    }

    // MARK: - Sync state

    func reloadSyncState() {
        syncState = SyncStateStore.shared.load()
    }

    func resetSyncState() {
        syncState = .empty
        SyncStateStore.shared.clear()
        statusMessage = "Sync state reset"
    }

    func saveSyncState() {
        SyncStateStore.shared.save(syncState)
    }

    // MARK: - Payload helpers

    func updatePayloadPreview(_ preview: String) {
        payloadPreview = preview
    }

    func updatePayloadSummary(_ summary: String) {
        payloadSummary = summary
    }

    // MARK: - Private

    private static func mapAuthorizationStatus(_ status: HKAuthorizationStatus) -> String {
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
    
    // MARK: - Payload preview

    func buildPayloadPreview(from payload: HealthSyncPayload) {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]

        do {
            let data = try encoder.encode(payload)
            let fullText = String(data: data, encoding: .utf8) ?? "Failed to render payload"

            let previewLimit = 4000
            if fullText.count > previewLimit {
                updatePayloadPreview(String(fullText.prefix(previewLimit)) + "\n\n... truncated ...")
            } else {
                updatePayloadPreview(fullText)
            }

            updatePayloadSummary(from: payload)
            statusMessage = "Payload preview built"

            syncState.lastPayloadGeneratedAt = Date()
            syncState.lastErrorMessage = nil
            syncState.lastSentItemCount = payloadItemCount(payload)
            saveSyncState()

        } catch {
            updatePayloadPreview("")
            statusMessage = "Payload build error: \(error.localizedDescription)"
            syncState.lastErrorMessage = error.localizedDescription
            saveSyncState()
        }
    }
    
    // MARK: - Sending

    func sendPayload(
        _ payload: HealthSyncPayload,
        mode: SyncMode,
        completion: @escaping () -> Void
    ) {
        statusMessage = "Sending..."

        let itemCount = payloadItemCount(payload)

        SyncService.shared.sendPayload(payload) { [weak self] result in
            guard let self else {
                completion()
                return
            }

            switch result {
            case .success:
                self.statusMessage = mode == .full ? "Full sync sent" : "Incremental sent"
                self.syncState.lastSuccessfulSyncAt = Date()
                self.syncState.lastPayloadGeneratedAt = Date()
                self.syncState.lastErrorMessage = nil
                self.syncState.lastSentItemCount = itemCount
                self.syncState.lastSyncMode = mode
                self.saveSyncState()

            case .failure(let error):
                self.statusMessage = "Send error: \(error.localizedDescription)"
                self.syncState.lastPayloadGeneratedAt = Date()
                self.syncState.lastErrorMessage = error.localizedDescription
                self.saveSyncState()
            }

            completion()
        }
    }
    
    // MARK: - Full sync

    func performFullSync(
        completion: @escaping (Result<FullSyncData, Error>) -> Void
    ) {
        guard !isSyncInProgress else { return }

        isSyncInProgress = true
        statusMessage = "Running full sync..."

        SyncService.shared.performFullSync { [weak self] result in
            guard let self else {
                completion(result)
                return
            }

            switch result {
            case .success(let data):
                self.updatePayloadSummary(from: data.payload)
                completion(.success(data))

            case .failure(let error):
                self.statusMessage = "Full sync error: \(error.localizedDescription)"
                self.syncState.lastErrorMessage = error.localizedDescription
                self.saveSyncState()
                self.isSyncInProgress = false
                completion(.failure(error))
            }
        }
    }
    
    // MARK: - Incremental sync

    func performIncrementalSync(
        completion: @escaping (Result<IncrementalSyncData, Error>) -> Void
    ) {
        guard !isSyncInProgress else { return }

        isSyncInProgress = true
        statusMessage = "Running incremental sync..."

        SyncService.shared.performIncrementalSync { [weak self] result in
            guard let self else {
                completion(result)
                return
            }

            switch result {
            case .success(let data):
                if let payload = data.payload {
                    self.updatePayloadSummary(from: payload)
                } else {
                    self.updatePayloadSummary(from: HealthSyncPayload(
                        generatedAt: ISO8601DateFormatter().string(from: Date()),
                        timezone: TimeZone.current.identifier,
                        sleepNights: [],
                        restingHeartRateDaily: [],
                        hrvSamples: [],
                        latestWeight: nil
                    ))

                    self.statusMessage = "Incremental sync: no new data"
                    self.syncState.lastErrorMessage = nil
                    self.syncState.lastSyncMode = .incremental
                    self.saveSyncState()
                    self.isSyncInProgress = false
                }

                completion(.success(data))

            case .failure(let error):
                self.statusMessage = "Incremental sync error: \(error.localizedDescription)"
                self.syncState.lastErrorMessage = error.localizedDescription
                self.saveSyncState()
                self.isSyncInProgress = false
                completion(.failure(error))
            }
        }
    }
    
    // MARK: - Manual sample reading

    func readSampleData(completion: @escaping (Result<SampleReadResult, Error>) -> Void) {
        statusMessage = "Reading sample data..."

        HealthKitService.shared.fetchLatestWeightSample { weightResult in
            switch weightResult {
            case .success(let weights):
                HealthKitService.shared.fetchRestingHRSamplesForLast7Days { restingHRResult in
                    switch restingHRResult {
                    case .success(let restingHR):
                        HealthKitService.shared.fetchHRVSamplesForLast7Days { hrvResult in
                            switch hrvResult {
                            case .success(let hrv):
                                HealthKitService.shared.fetchSleepSamplesForLast7Days { sleepResult in
                                    switch sleepResult {
                                    case .success(let sleep):
                                        let sleepNightAggregates = HealthKitService.shared.buildSleepNightAggregates(from: sleep)

                                        self.statusMessage = "Sample data loaded"

                                        completion(.success(
                                            SampleReadResult(
                                                weightSamples: weights,
                                                restingHRSamples: restingHR,
                                                hrvSamples: hrv,
                                                sleepSamples: sleep,
                                                sleepNightAggregates: sleepNightAggregates
                                            )
                                        ))

                                    case .failure(let error):
                                        self.statusMessage = "Sleep read error: \(error.localizedDescription)"
                                        completion(.failure(error))
                                    }
                                }

                            case .failure(let error):
                                self.statusMessage = "HRV read error: \(error.localizedDescription)"
                                completion(.failure(error))
                            }
                        }

                    case .failure(let error):
                        self.statusMessage = "Resting HR read error: \(error.localizedDescription)"
                        completion(.failure(error))
                    }
                }

            case .failure(let error):
                self.statusMessage = "Weight read error: \(error.localizedDescription)"
                completion(.failure(error))
            }
        }
    }
    
    // MARK: - Startup logic

    private var hasPerformedInitialSync = false

    func performInitialSyncIfNeeded(
        completion: @escaping (Result<IncrementalSyncData, Error>) -> Void
    ) {
        guard !hasPerformedInitialSync else { return }
        guard !isSyncInProgress else { return }

        hasPerformedInitialSync = true

        statusMessage = "Initial sync..."

        performIncrementalSync { result in
            completion(result)
        }
    }

    func updatePayloadSummary(from payload: HealthSyncPayload) {
        let encoder = JSONEncoder()

        do {
            let data = try encoder.encode(payload)
            let itemCount = payloadItemCount(payload)

            if itemCount == 0 {
                updatePayloadSummary("""
    No incremental payload data
    payloadSizeBytes: \(data.count)
    """)
                return
            }

            updatePayloadSummary("""
    sleepNights: \(payload.sleepNights.count)
    restingHeartRateDaily: \(payload.restingHeartRateDaily.count)
    hrvSamples: \(payload.hrvSamples.count)
    latestWeight: \(payload.latestWeight == nil ? 0 : 1)
    payloadSizeBytes: \(data.count)
    """)
        } catch {
            updatePayloadSummary("Failed to build payload summary")
        }
    }

    func payloadItemCount(_ payload: HealthSyncPayload) -> Int {
        payload.sleepNights.count +
        payload.restingHeartRateDaily.count +
        payload.hrvSamples.count +
        (payload.latestWeight == nil ? 0 : 1)
    }
}
