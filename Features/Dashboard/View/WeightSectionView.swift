//
//  WeightSectionView.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 06.04.2026.
//

import SwiftUI

struct WeightSectionView: View {
    let samples: [WeightSample]
    let formatDate: (Date) -> String

    var body: some View {
        GroupBox("Weight samples") {
            if samples.isEmpty {
                Text("No weight samples")
                    .foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(samples.prefix(5)) { sample in
                        Text("\(formatDate(sample.date))  •  \(sample.kilograms, specifier: "%.1f") kg")
                    }
                }
            }
        }
    }
}

#Preview {
    WeightSectionView(
        samples: [],
        formatDate: { _ in "01/01/25" }
    )
}
