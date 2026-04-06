//
//  SleepNightAggregatesSectionView.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 06.04.2026.
//

import SwiftUI

struct SleepNightAggregatesSectionView: View {
    let nights: [SleepNightAggregate]
    let formatDate: (Date) -> String
    let formatDateOnly: (Date) -> String

    var body: some View {
        GroupBox("Sleep night aggregates") {
            if nights.isEmpty {
                Text("No sleep aggregates")
                    .foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 12) {
                    ForEach(nights.prefix(5)) { night in
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Wake date: \(formatDateOnly(night.wakeDate))")
                                .font(.headline)

                            Text("Sleep: \(night.totalSleepMinutes, specifier: "%.0f") min")
                            Text("Awake: \(night.awakeMinutes, specifier: "%.0f") min")
                            Text("Core: \(night.coreMinutes, specifier: "%.0f") min")
                            Text("REM: \(night.remMinutes, specifier: "%.0f") min")
                            Text("Deep: \(night.deepMinutes, specifier: "%.0f") min")
                            Text("In Bed: \(night.inBedMinutes, specifier: "%.0f") min")

                            Text("\(formatDate(night.sleepStart)) → \(formatDate(night.sleepEnd))")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
        }
    }
}

#Preview {
    SleepNightAggregatesSectionView(
        nights: [],
        formatDate: { _ in "01/01/25, 09:00" },
        formatDateOnly: { _ in "Jan 1, 2025" }
    )
}
