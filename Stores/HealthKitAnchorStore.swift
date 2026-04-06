//
//  HealthKitAnchorStore.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 06.04.2026.
//

import Foundation
import HealthKit

final class HealthKitAnchorStore {
    static let shared = HealthKitAnchorStore()

    private let userDefaults = UserDefaults.standard

    private init() {}

    private func key(for type: String) -> String {
        return "healthkit.anchor.\(type)"
    }

    func loadAnchor(for type: String) -> HKQueryAnchor? {
        guard let data = userDefaults.data(forKey: key(for: type)) else {
            return nil
        }

        return try? NSKeyedUnarchiver.unarchivedObject(ofClass: HKQueryAnchor.self, from: data)
    }

    func saveAnchor(_ anchor: HKQueryAnchor, for type: String) {
        if let data = try? NSKeyedArchiver.archivedData(withRootObject: anchor, requiringSecureCoding: true) {
            userDefaults.set(data, forKey: key(for: type))
        }
    }

    func clearAnchor(for type: String) {
        userDefaults.removeObject(forKey: key(for: type))
    }
}
