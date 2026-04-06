//
//  RestingHRSectionView.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 06.04.2026.
//

import SwiftUI

struct RestingHRSectionView: View {
    let samples: [RestingHRSample]
    let formatDate: (Date) -> String

    var body: some View {
        GroupBox("Resting HR samples") {
            if samples.isEmpty {
                Text("No resting HR samples")
                    .foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(samples.prefix(5)) { sample in
                        Text("\(formatDate(sample.date))  •  \(sample.bpm, specifier: "%.0f") bpm")
                    }
                }
            }
        }
    }
}

#Preview {
    RestingHRSectionView(
        samples: [],
        formatDate: { _ in "01/01/25, 09:00" }
    )
}
