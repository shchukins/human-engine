//
//  HealthSyncModels.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 06.04.2026.
//

import Foundation

struct SleepNightDTO: Codable {
    let wakeDate: String
    let sleepStart: String
    let sleepEnd: String

    let totalSleepMinutes: Double
    let awakeMinutes: Double
    let coreMinutes: Double
    let remMinutes: Double
    let deepMinutes: Double
    let inBedMinutes: Double?
}

struct RestingHRDailyDTO: Codable {
    let date: String
    let bpm: Double
}

struct HRVSampleDTO: Codable {
    let startAt: String
    let valueMs: Double
}

struct LatestWeightDTO: Codable {
    let measuredAt: String
    let kilograms: Double
}

struct HealthSyncPayload: Codable {
    let generatedAt: String
    let timezone: String

    let sleepNights: [SleepNightDTO]
    let restingHeartRateDaily: [RestingHRDailyDTO]
    let hrvSamples: [HRVSampleDTO]
    let latestWeight: LatestWeightDTO?
}
