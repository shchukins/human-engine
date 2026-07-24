import Foundation
import Testing
@testable import HumanEngineIOS

@MainActor
struct SyncCoordinatorTests {
    @Test
    func startupSyncSendsRecoveryPayload() {
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let payload = makePayload(sleep: 7, hrv: 76, restingHR: 6, valueOffset: 0)
        let service = FakeAutoSyncService(payload: payload)
        let store = InMemorySyncStateStore()
        let coordinator = makeCoordinator(service: service, store: store, now: now)

        coordinator.triggerSync(reason: .appLaunch)

        #expect(service.recoverySyncCallCount == 1)
        #expect(service.sentPayloads.count == 1)
        #expect(service.sentPayloads.first?.sleepNights.count == 7)
        #expect(service.sentPayloads.first?.hrvSamples.count == 76)
        #expect(service.sentPayloads.first?.restingHeartRateDaily.count == 6)
        #expect(store.state.lastSyncMode == .full)
        #expect(store.state.lastRecoveryPayloadFingerprint == RecoveryPayloadFingerprint.make(from: payload))
    }

    @Test
    func repeatedForegroundInCooldownDoesNotDuplicateSync() {
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let payload = makePayload(sleep: 7, hrv: 76, restingHR: 6, valueOffset: 0)
        let service = FakeAutoSyncService(payload: payload)
        let store = InMemorySyncStateStore(
            state: SyncState(
                lastSyncAttemptAt: now.addingTimeInterval(-60),
                lastSuccessfulSyncAt: now.addingTimeInterval(-60),
                lastPayloadGeneratedAt: now.addingTimeInterval(-60),
                lastErrorMessage: nil,
                lastSentItemCount: 89,
                lastSyncMode: .full,
                hasPendingAutoSync: false,
                lastRecoveryPayloadFingerprint: RecoveryPayloadFingerprint.make(from: payload)
            )
        )
        let coordinator = makeCoordinator(service: service, store: store, now: now)

        coordinator.handleAppBecameActive()

        #expect(service.recoverySyncCallCount == 0)
        #expect(service.sentPayloads.isEmpty)
        #expect(store.state.hasPendingAutoSync == false)
    }

    @Test
    func newRecoveryDataBypassesOldCachedState() {
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let oldPayload = makePayload(sleep: 7, hrv: 76, restingHR: 6, valueOffset: 0)
        let newPayload = makePayload(sleep: 7, hrv: 76, restingHR: 6, valueOffset: 1)
        let service = FakeAutoSyncService(payload: newPayload)
        let store = InMemorySyncStateStore(
            state: SyncState(
                lastSyncAttemptAt: now.addingTimeInterval(-3_600),
                lastSuccessfulSyncAt: now.addingTimeInterval(-3_600),
                lastPayloadGeneratedAt: now.addingTimeInterval(-3_600),
                lastErrorMessage: nil,
                lastSentItemCount: 89,
                lastSyncMode: .full,
                hasPendingAutoSync: false,
                lastRecoveryPayloadFingerprint: RecoveryPayloadFingerprint.make(from: oldPayload)
            )
        )
        let coordinator = makeCoordinator(service: service, store: store, now: now)

        coordinator.handleAppBecameActive()

        #expect(service.sentPayloads.count == 1)
        #expect(store.state.lastRecoveryPayloadFingerprint == RecoveryPayloadFingerprint.make(from: newPayload))
    }

    @Test
    func manualFullSyncFingerprintRemainsCompatibleWithAutoRecoveryPayload() {
        let payload = makePayload(sleep: 7, hrv: 76, restingHR: 6, valueOffset: 0)

        let manualFingerprint = RecoveryPayloadFingerprint.make(from: payload)
        let autoRecoveryFingerprint = RecoveryPayloadFingerprint.make(from: payload)

        #expect(manualFingerprint == autoRecoveryFingerprint)
        #expect(payload.sleepNights.count == 7)
        #expect(payload.hrvSamples.count == 76)
        #expect(payload.restingHeartRateDaily.count == 6)
    }

    private func makeCoordinator(
        service: FakeAutoSyncService,
        store: InMemorySyncStateStore,
        now: Date
    ) -> SyncCoordinator {
        SyncCoordinator(
            notificationCenter: NotificationCenter(),
            syncService: service,
            syncStateStore: store,
            healthKitAuthorizationProvider: FakeHealthKitAuthorizationProvider(),
            now: { now },
            debounceInterval: 0,
            lifecycleCooldownInterval: 15 * 60
        )
    }

    private func makePayload(
        sleep: Int,
        hrv: Int,
        restingHR: Int,
        valueOffset: Double
    ) -> HealthSyncPayload {
        HealthSyncPayload(
            generatedAt: "2026-07-25T06:00:00Z",
            timezone: "Europe/Moscow",
            sleepNights: (0..<sleep).map { index in
                SleepNightDTO(
                    wakeDate: "2026-07-\(String(format: "%02d", 25 - index))",
                    sleepStart: "2026-07-\(String(format: "%02d", 24 - index))T22:00:00Z",
                    sleepEnd: "2026-07-\(String(format: "%02d", 25 - index))T05:00:00Z",
                    totalSleepMinutes: 420 + valueOffset,
                    awakeMinutes: 12,
                    coreMinutes: 250,
                    remMinutes: 95,
                    deepMinutes: 75,
                    inBedMinutes: nil
                )
            },
            restingHeartRateDaily: (0..<restingHR).map { index in
                RestingHRDailyDTO(
                    date: "2026-07-\(String(format: "%02d", 25 - index))",
                    bpm: 48 + Double(index) + valueOffset
                )
            },
            hrvSamples: (0..<hrv).map { index in
                HRVSampleDTO(
                    startAt: "2026-07-25T\(String(format: "%02d", index % 24)):00:00Z",
                    valueMs: 65 + Double(index) + valueOffset
                )
            },
            latestWeight: nil
        )
    }
}

private final class FakeAutoSyncService: AutoSyncServicing {
    private let payload: HealthSyncPayload
    var recoverySyncCallCount = 0
    var sentPayloads: [HealthSyncPayload] = []

    init(payload: HealthSyncPayload) {
        self.payload = payload
    }

    func performRecoverySync(completion: @escaping (Result<FullSyncData, Error>) -> Void) {
        recoverySyncCallCount += 1
        completion(.success(
            FullSyncData(
                weightSamples: [],
                restingHRSamples: [],
                hrvSamples: [],
                sleepSamples: [],
                sleepNightAggregates: [],
                payload: payload
            )
        ))
    }

    func sendPayload(
        _ payload: HealthSyncPayload,
        userID: String,
        completion: @escaping (Result<HealthIngestAndProcessResponse, Error>) -> Void
    ) {
        sentPayloads.append(payload)
        completion(.success(
            HealthIngestAndProcessResponse(
                ok: true,
                userId: userID,
                affectedDates: ["2026-07-25"],
                sleepNightsCount: payload.sleepNights.count,
                restingHrCount: payload.restingHeartRateDaily.count,
                hrvCount: payload.hrvSamples.count,
                latestWeightIncluded: payload.latestWeight != nil,
                recoveryDaysRecomputed: 1,
                readinessDaysRecomputed: 1
            )
        ))
    }
}

private final class FakeHealthKitAuthorizationProvider: HealthKitAuthorizationProviding {
    var hasRequestedAuthorization = true

    func enableObservers() {}
}

private final class InMemorySyncStateStore: SyncStateStoring {
    var state: SyncState

    init(state: SyncState = .empty) {
        self.state = state
    }

    func load() -> SyncState {
        state
    }

    func save(_ state: SyncState) {
        self.state = state
    }
}
