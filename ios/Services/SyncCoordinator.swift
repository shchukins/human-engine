import Foundation

enum AutoSyncReason: String {
    case appLaunch = "app_launch"
    case appBecameActive = "app_became_active"
    case healthKitHRVUpdated = "healthkit_hrv_updated"
    case healthKitRestingHRUpdated = "healthkit_resting_hr_updated"
    case healthKitSleepUpdated = "healthkit_sleep_updated"
    case pendingRetry = "pending_retry"
}

protocol HealthKitAuthorizationProviding {
    var hasRequestedAuthorization: Bool { get }
    func enableObservers()
}

protocol AutoSyncServicing {
    func performRecoverySync(completion: @escaping (Result<FullSyncData, Error>) -> Void)
    func sendPayload(
        _ payload: HealthSyncPayload,
        userID: String,
        completion: @escaping (Result<HealthIngestAndProcessResponse, Error>) -> Void
    )
}

protocol SyncStateStoring {
    func load() -> SyncState
    func save(_ state: SyncState)
}

extension HealthKitService: HealthKitAuthorizationProviding {}
extension SyncService: AutoSyncServicing {}
extension SyncStateStore: SyncStateStoring {}

enum RecoveryPayloadFingerprint {
    static func make(from payload: HealthSyncPayload) -> String {
        let sleep = payload.sleepNights
            .map { "\($0.wakeDate):\($0.sleepStart):\($0.sleepEnd):\($0.totalSleepMinutes):\($0.awakeMinutes):\($0.coreMinutes):\($0.remMinutes):\($0.deepMinutes):\($0.inBedMinutes ?? -1)" }
            .sorted()
            .joined(separator: "|")
        let restingHR = payload.restingHeartRateDaily
            .map { "\($0.date):\($0.bpm)" }
            .sorted()
            .joined(separator: "|")
        let hrv = payload.hrvSamples
            .map { "\($0.startAt):\($0.valueMs)" }
            .sorted()
            .joined(separator: "|")

        return "sleep[\(sleep)]::rhr[\(restingHR)]::hrv[\(hrv)]"
    }
}

@MainActor
final class SyncCoordinator {
    static let shared = SyncCoordinator()

    private let notificationCenter: NotificationCenter
    private let syncService: AutoSyncServicing
    private let syncStateStore: SyncStateStoring
    private let healthKitAuthorizationProvider: HealthKitAuthorizationProviding
    private let now: () -> Date
    private let debounceInterval: TimeInterval
    private let lifecycleCooldownInterval: TimeInterval
    private let backendUserID = "sergey"

    private var observerTokens: [NSObjectProtocol] = []
    private var hasStarted = false
    private var shouldSyncAgainAfterCurrentRun = false

    private(set) var isSyncRunning = false
    private(set) var hasPendingSync: Bool
    private(set) var lastSyncAttemptAt: Date?
    private var debounceWorkItem: DispatchWorkItem?

    init(
        notificationCenter: NotificationCenter = .default,
        syncService: AutoSyncServicing? = nil,
        syncStateStore: SyncStateStoring? = nil,
        healthKitAuthorizationProvider: HealthKitAuthorizationProviding? = nil,
        now: @escaping () -> Date = Date.init,
        debounceInterval: TimeInterval = 5,
        lifecycleCooldownInterval: TimeInterval = 15 * 60
    ) {
        let syncService = syncService ?? SyncService.shared
        let syncStateStore = syncStateStore ?? SyncStateStore.shared
        let healthKitAuthorizationProvider = healthKitAuthorizationProvider ?? HealthKitService.shared

        self.notificationCenter = notificationCenter
        self.syncService = syncService
        self.syncStateStore = syncStateStore
        self.healthKitAuthorizationProvider = healthKitAuthorizationProvider
        self.now = now
        self.debounceInterval = debounceInterval
        self.lifecycleCooldownInterval = lifecycleCooldownInterval

        let syncState = syncStateStore.load()
        self.hasPendingSync = syncState.hasPendingAutoSync
        self.lastSyncAttemptAt = syncState.lastSyncAttemptAt
    }

    func start() {
        guard !hasStarted else { return }

        hasStarted = true
        print("sync_coordinator_start")

        registerHealthKitObservers()
        healthKitAuthorizationProvider.enableObservers()
    }

    func retryPendingSyncAfterAuthorizationIfNeeded() {
        let syncState = syncStateStore.load()
        hasPendingSync = syncState.hasPendingAutoSync
        lastSyncAttemptAt = syncState.lastSyncAttemptAt

        guard hasPendingSync else {
            notificationCenter.post(name: .syncStateDidChange, object: nil)
            return
        }

        triggerSync(reason: .pendingRetry)
    }

    func handleAppBecameActive() {
        triggerSync(reason: hasPendingSync ? .pendingRetry : .appBecameActive)
    }

    func handleHealthKitUpdate(reason: AutoSyncReason) {
        triggerSyncDebounced(reason: hasPendingSync ? .pendingRetry : reason)
    }

    func triggerSyncDebounced(reason: AutoSyncReason) {
        debounceWorkItem?.cancel()

        let workItem = DispatchWorkItem { [weak self] in
            Task { @MainActor [weak self] in
                guard let self else { return }
                self.triggerSync(reason: reason)
            }
        }

        debounceWorkItem = workItem
        DispatchQueue.main.asyncAfter(deadline: .now() + debounceInterval, execute: workItem)
    }

    func triggerSync(reason: AutoSyncReason) {
        print("auto_sync_triggered reason=\(reason.rawValue)")

        guard healthKitAuthorizationProvider.hasRequestedAuthorization else {
            print("auto_sync_failed reason=\(reason.rawValue) error=healthkit_permissions_required")
            hasPendingSync = false
            saveSyncState { syncState in
                syncState.lastErrorMessage = "HealthKit permissions required"
                syncState.hasPendingAutoSync = false
            }
            notificationCenter.post(name: .syncStateDidChange, object: nil)
            return
        }

        if isSyncRunning {
            shouldSyncAgainAfterCurrentRun = true
            print("auto_sync_skipped_already_running reason=\(reason.rawValue)")
            return
        }

        if shouldSkipLifecycleCooldown(for: reason) {
            print("auto_sync_skipped_cooldown reason=\(reason.rawValue)")
            return
        }

        isSyncRunning = true
        lastSyncAttemptAt = now()

        saveSyncState { syncState in
            syncState.lastSyncAttemptAt = self.lastSyncAttemptAt
            syncState.lastErrorMessage = nil
        }

        print("auto_sync_started reason=\(reason.rawValue)")

        syncService.performRecoverySync { [weak self] result in
            guard let self else { return }

            switch result {
            case .success(let data):
                self.handleRecoveryPayload(data.payload, reason: reason)

            case .failure(let error):
                print("auto_sync_failed reason=\(reason.rawValue) error=\(error.localizedDescription)")
                self.markPendingSync(errorMessage: error.localizedDescription)
                self.finishSync(success: false)
            }
        }
    }

    private func handleRecoveryPayload(_ payload: HealthSyncPayload, reason: AutoSyncReason) {
        let itemCounts = recoveryItemCounts(payload)
        let fingerprint = RecoveryPayloadFingerprint.make(from: payload)
        let syncState = syncStateStore.load()
        let hasPayloadData = itemCounts.sleep > 0 || itemCounts.hrv > 0 || itemCounts.restingHR > 0
        let hasNewRecoveryData = fingerprint != syncState.lastRecoveryPayloadFingerprint
        let shouldSendPending = hasPendingSync || syncState.hasPendingAutoSync
        let shouldSendFirstPayload = syncState.lastSuccessfulSyncAt == nil && hasPayloadData

        if !hasNewRecoveryData && !shouldSendPending && !shouldSendFirstPayload {
            if isLifecycleReason(reason), isWithinLifecycleCooldown(syncState) {
                print("auto_sync_skipped_cooldown reason=\(reason.rawValue)")
            } else {
                print("auto_sync_skipped_no_new_data reason=\(reason.rawValue)")
            }

            hasPendingSync = false
            saveSyncState { syncState in
                syncState.lastErrorMessage = nil
                syncState.lastSyncMode = .full
                syncState.hasPendingAutoSync = false
            }
            finishSync(success: true)
            return
        }

        if !hasPayloadData {
            print("auto_sync_skipped_no_new_data reason=\(reason.rawValue)")
            hasPendingSync = false
            saveSyncState { syncState in
                syncState.lastErrorMessage = nil
                syncState.lastSyncMode = .full
                syncState.hasPendingAutoSync = false
                syncState.lastRecoveryPayloadFingerprint = fingerprint
            }
            finishSync(success: true)
            return
        }

        print(
            "auto_sync_send_started reason=\(reason.rawValue) " +
            "sleep=\(itemCounts.sleep) hrv=\(itemCounts.hrv) rhr=\(itemCounts.restingHR)"
        )

        syncService.sendPayload(payload, userID: backendUserID) { [weak self] sendResult in
            guard let self else { return }

            switch sendResult {
            case .success(let response):
                print(
                    "auto_sync_success reason=\(reason.rawValue) " +
                    "sleep=\(itemCounts.sleep) hrv=\(itemCounts.hrv) rhr=\(itemCounts.restingHR) " +
                    "affected_dates=\(response.affectedDates.count) " +
                    "recovery=\(response.recoveryDaysRecomputed) " +
                    "readiness=\(response.readinessDaysRecomputed)"
                )

                self.hasPendingSync = false
                self.saveSyncState { syncState in
                    syncState.lastSuccessfulSyncAt = self.now()
                    syncState.lastPayloadGeneratedAt = self.now()
                    syncState.lastErrorMessage = nil
                    syncState.lastSentItemCount = self.payloadItemCount(payload)
                    syncState.lastSyncMode = .full
                    syncState.hasPendingAutoSync = false
                    syncState.lastRecoveryPayloadFingerprint = fingerprint
                }
                self.finishSync(success: true)

            case .failure(let error):
                print("auto_sync_failed reason=\(reason.rawValue) error=\(error.localizedDescription)")
                self.markPendingSync(errorMessage: error.localizedDescription)
                self.finishSync(success: false)
            }
        }
    }

    private func registerHealthKitObservers() {
        observerTokens.append(
            notificationCenter.addObserver(
                forName: .healthKitHRVUpdated,
                object: nil,
                queue: .main
            ) { [weak self] _ in
                Task { @MainActor [weak self] in
                    guard let self else { return }
                    self.handleHealthKitUpdate(reason: .healthKitHRVUpdated)
                }
            }
        )

        observerTokens.append(
            notificationCenter.addObserver(
                forName: .healthKitRestingHRUpdated,
                object: nil,
                queue: .main
            ) { [weak self] _ in
                Task { @MainActor [weak self] in
                    guard let self else { return }
                    self.handleHealthKitUpdate(reason: .healthKitRestingHRUpdated)
                }
            }
        )

        observerTokens.append(
            notificationCenter.addObserver(
                forName: .healthKitSleepUpdated,
                object: nil,
                queue: .main
            ) { [weak self] _ in
                Task { @MainActor [weak self] in
                    guard let self else { return }
                    self.handleHealthKitUpdate(reason: .healthKitSleepUpdated)
                }
            }
        )
    }

    private func isWithinLifecycleCooldown(_ syncState: SyncState) -> Bool {
        guard let lastSuccessfulSyncAt = syncState.lastSuccessfulSyncAt else {
            return false
        }

        return now().timeIntervalSince(lastSuccessfulSyncAt) < lifecycleCooldownInterval
    }

    private func shouldSkipLifecycleCooldown(for reason: AutoSyncReason) -> Bool {
        guard isLifecycleReason(reason), !hasPendingSync else {
            return false
        }

        let syncState = syncStateStore.load()
        return !syncState.hasPendingAutoSync && isWithinLifecycleCooldown(syncState)
    }

    private func isLifecycleReason(_ reason: AutoSyncReason) -> Bool {
        reason == .appLaunch || reason == .appBecameActive
    }

    private func markPendingSync(errorMessage: String) {
        hasPendingSync = true
        saveSyncState { syncState in
            syncState.lastErrorMessage = errorMessage
            syncState.hasPendingAutoSync = true
            syncState.lastSyncMode = .full
        }
    }

    private func finishSync(success: Bool) {
        isSyncRunning = false
        notificationCenter.post(name: .syncStateDidChange, object: nil)

        if success {
            notificationCenter.post(name: .autoSyncDidFinish, object: nil)
        }

        if shouldSyncAgainAfterCurrentRun {
            shouldSyncAgainAfterCurrentRun = false
            triggerSync(reason: .pendingRetry)
        }
    }

    private func saveSyncState(_ mutate: (inout SyncState) -> Void) {
        var syncState = syncStateStore.load()
        mutate(&syncState)
        syncStateStore.save(syncState)

        let lastSuccessfulSyncAt = syncState.lastSuccessfulSyncAt?.description ?? "nil"
        let lastSyncAttemptAt = syncState.lastSyncAttemptAt?.description ?? "nil"

        print(
            "sync_state_saved " +
            "lastSuccessfulSyncAt=\(lastSuccessfulSyncAt) " +
            "lastSyncAttemptAt=\(lastSyncAttemptAt) " +
            "hasPendingAutoSync=\(syncState.hasPendingAutoSync)"
        )
    }

    private func payloadItemCount(_ payload: HealthSyncPayload) -> Int {
        payload.sleepNights.count +
        payload.restingHeartRateDaily.count +
        payload.hrvSamples.count +
        (payload.latestWeight == nil ? 0 : 1)
    }

    private func recoveryItemCounts(_ payload: HealthSyncPayload) -> (sleep: Int, hrv: Int, restingHR: Int) {
        (
            sleep: payload.sleepNights.count,
            hrv: payload.hrvSamples.count,
            restingHR: payload.restingHeartRateDaily.count
        )
    }
}
