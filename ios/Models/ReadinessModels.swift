//
//  ReadinessModels.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 17.04.2026.
//

import Foundation

struct ReadinessDailyResponse: Decodable {
    let ok: Bool
    let userId: String
    let date: String
    let readinessScore: Double?
    let goodDayProbability: Double?
    let statusText: String?
    let explanation: ReadinessExplanation?
}

struct ReadinessExplanation: Decodable {
    let freshness: Double?
    let freshnessNorm: Double?
    let recoveryScoreSimple: Double?
    let formula: String?
    let recoveryExplanation: RecoveryExplanation?
}

struct RecoveryExplanation: Decodable {
    let method: String?
    let sleepMinutes: Double?
    let hrvToday: Double?
    let rhrToday: Double?
    let hrvBaseline: Double?
    let rhrBaseline: Double?
    let hrvDev: Double?
    let rhrDev: Double?
    let sleepScore: Double?
    let hrvScore: Double?
    let rhrScore: Double?
    let recoveryScoreSimple: Double?
}
