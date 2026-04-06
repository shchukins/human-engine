//
//  HRVSectionView.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 06.04.2026.
//

import SwiftUI

struct HRVSectionView: View {
    let samples: [HRVSample]
    let formatDate: (Date) -> String

    var body: some View {
        GroupBox("HRV samples") {
            if samples.isEmpty {
                Text("No HRV samples")
                    .foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(samples.prefix(5)) { sample in
                        Text("\(formatDate(sample.date))  •  \(sample.milliseconds, specifier: "%.1f") ms")
                    }
                }
            }
        }
    }
}

#Preview {
    HRVSectionView(
        samples: [],
        formatDate: { _ in "01/01/25, 09:00" }
    )
}
