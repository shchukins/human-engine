//
//  HealthSamples.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 06.04.2026.
//

import Foundation

// MARK: - Raw / near-raw HealthKit samples used inside the iOS app

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

struct SleepSample: Identifiable {
    let id = UUID()
    let startDate: Date
    let endDate: Date
    let durationMinutes: Double
    let stage: String
}

// MARK: - Aggregated sleep model used for payload building and UI

struct SleepNightAggregate: Identifiable {
    let id = UUID()
    let wakeDate: Date
    let sleepStart: Date
    let sleepEnd: Date

    let totalSleepMinutes: Double
    let awakeMinutes: Double
    let coreMinutes: Double
    let remMinutes: Double
    let deepMinutes: Double
    let inBedMinutes: Double
}
