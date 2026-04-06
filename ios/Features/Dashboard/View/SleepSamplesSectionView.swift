//
//  SleepSamplesSectionView.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 06.04.2026.
//

import SwiftUI

struct SleepSamplesSectionView: View {
    let samples: [SleepSample]
    let formatDate: (Date) -> String

    var body: some View {
        GroupBox("Sleep samples") {
            if samples.isEmpty {
                Text("No sleep samples")
                    .foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(samples.prefix(10)) { sample in
                        VStack(alignment: .leading, spacing: 2) {
                            Text("\(sample.stage)  •  \(sample.durationMinutes, specifier: "%.0f") min")
                            Text("\(formatDate(sample.startDate)) → \(formatDate(sample.endDate))")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
        }
    }
}

#Preview {
    SleepSamplesSectionView(
        samples: [],
        formatDate: { _ in "01/01/25, 09:00" }
    )
}
