//
//  HealthKitService.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 05.04.2026.
//

import Foundation
import HealthKit

struct WeightSample: Identifiable {
    let id = UUID()
    let date: Date
    let kilograms: Double
}

struct RestingHRSample: Identifiable {
    let id = UUID()
    let date: Date
    let bpm: Double
}

struct HRVSample: Identifiable {
    let id = UUID()
    let date: Date
    let milliseconds: Double
}

final class HealthKitService {
    static let shared = HealthKitService()

    private let healthStore = HKHealthStore()

    private init() {}

    var isHealthDataAvailable: Bool {
        HKHealthStore.isHealthDataAvailable()
    }

    func requestAuthorization(completion: @escaping (Result<Void, Error>) -> Void) {
        guard isHealthDataAvailable else {
            completion(.failure(HealthKitError.notAvailable))
            return
        }

        guard
            let sleepType = HKObjectType.categoryType(forIdentifier: .sleepAnalysis),
            let hrvType = HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN),
            let restingHeartRateType = HKObjectType.quantityType(forIdentifier: .restingHeartRate),
            let bodyMassType = HKObjectType.quantityType(forIdentifier: .bodyMass)
        else {
            completion(.failure(HealthKitError.typeNotAvailable))
            return
        }

        let readTypes: Set<HKObjectType> = [
            sleepType,
            hrvType,
            restingHeartRateType,
            bodyMassType
        ]

        healthStore.requestAuthorization(toShare: nil, read: readTypes) { success, error in
            DispatchQueue.main.async {
                if let error = error {
                    completion(.failure(error))
                    return
                }

                if success {
                    completion(.success(()))
                } else {
                    completion(.failure(HealthKitError.authorizationFailed))
                }
            }
        }
    }

    func authorizationStatuses() -> [String: HKAuthorizationStatus] {
        var result: [String: HKAuthorizationStatus] = [:]

        if let sleepType = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) {
            result["Sleep"] = healthStore.authorizationStatus(for: sleepType)
        }

        if let hrvType = HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN) {
            result["HRV"] = healthStore.authorizationStatus(for: hrvType)
        }

        if let restingHeartRateType = HKObjectType.quantityType(forIdentifier: .restingHeartRate) {
            result["Resting HR"] = healthStore.authorizationStatus(for: restingHeartRateType)
        }

        if let bodyMassType = HKObjectType.quantityType(forIdentifier: .bodyMass) {
            result["Weight"] = healthStore.authorizationStatus(for: bodyMassType)
        }

        return result
    }

    func fetchWeightSamplesForLast7Days(completion: @escaping (Result<[WeightSample], Error>) -> Void) {
        guard let bodyMassType = HKObjectType.quantityType(forIdentifier: .bodyMass) else {
            completion(.failure(HealthKitError.typeNotAvailable))
            return
        }

        let predicate = samplesPredicateForLast7Days()
        let sortDescriptors = [
            NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: false)
        ]

        let query = HKSampleQuery(
            sampleType: bodyMassType,
            predicate: predicate,
            limit: 20,
            sortDescriptors: sortDescriptors
        ) { _, samples, error in
            DispatchQueue.main.async {
                if let error {
                    completion(.failure(error))
                    return
                }

                let result = (samples as? [HKQuantitySample] ?? []).map { sample in
                    WeightSample(
                        date: sample.startDate,
                        kilograms: sample.quantity.doubleValue(for: .gramUnit(with: .kilo))
                    )
                }

                completion(.success(result))
            }
        }

        healthStore.execute(query)
    }

    func fetchRestingHRSamplesForLast7Days(completion: @escaping (Result<[RestingHRSample], Error>) -> Void) {
        guard let restingHeartRateType = HKObjectType.quantityType(forIdentifier: .restingHeartRate) else {
            completion(.failure(HealthKitError.typeNotAvailable))
            return
        }

        let predicate = samplesPredicateForLast7Days()
        let sortDescriptors = [
            NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: false)
        ]

        let query = HKSampleQuery(
            sampleType: restingHeartRateType,
            predicate: predicate,
            limit: 20,
            sortDescriptors: sortDescriptors
        ) { _, samples, error in
            DispatchQueue.main.async {
                if let error {
                    completion(.failure(error))
                    return
                }

                let unit = HKUnit.count().unitDivided(by: .minute())
                let result = (samples as? [HKQuantitySample] ?? []).map { sample in
                    RestingHRSample(
                        date: sample.startDate,
                        bpm: sample.quantity.doubleValue(for: unit)
                    )
                }

                completion(.success(result))
            }
        }

        healthStore.execute(query)
    }

    func fetchHRVSamplesForLast7Days(completion: @escaping (Result<[HRVSample], Error>) -> Void) {
        guard let hrvType = HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN) else {
            completion(.failure(HealthKitError.typeNotAvailable))
            return
        }

        let predicate = samplesPredicateForLast7Days()
        let sortDescriptors = [
            NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: false)
        ]

        let query = HKSampleQuery(
            sampleType: hrvType,
            predicate: predicate,
            limit: 50,
            sortDescriptors: sortDescriptors
        ) { _, samples, error in
            DispatchQueue.main.async {
                if let error {
                    completion(.failure(error))
                    return
                }

                let result = (samples as? [HKQuantitySample] ?? []).map { sample in
                    HRVSample(
                        date: sample.startDate,
                        milliseconds: sample.quantity.doubleValue(for: .secondUnit(with: .milli))
                    )
                }

                completion(.success(result))
            }
        }

        healthStore.execute(query)
    }

    private func samplesPredicateForLast7Days() -> NSPredicate {
        let startDate = Calendar.current.date(byAdding: .day, value: -7, to: Date()) ?? Date.distantPast
        return HKQuery.predicateForSamples(
            withStart: startDate,
            end: Date(),
            options: .strictStartDate
        )
    }
}

enum HealthKitError: LocalizedError {
    case notAvailable
    case typeNotAvailable
    case authorizationFailed

    var errorDescription: String? {
        switch self {
        case .notAvailable:
            return "Health data is not available on this device."
        case .typeNotAvailable:
            return "Required HealthKit data types are not available."
        case .authorizationFailed:
            return "HealthKit authorization was not granted."
        }
    }
}
