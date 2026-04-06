//
//  PayloadPreviewSectionView.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 06.04.2026.
//

import SwiftUI

struct PayloadPreviewSectionView: View {
    let payloadPreview: String

    var body: some View {
        GroupBox("Payload preview") {
            if payloadPreview.isEmpty {
                Text("No payload yet")
                    .foregroundStyle(.secondary)
            } else {
                ScrollView(.horizontal) {
                    Text(payloadPreview)
                        .font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }
}

#Preview {
    PayloadPreviewSectionView(
        payloadPreview: """
        {
          "sleepNights": [],
          "hrvSamples": []
        }
        """
    )
}
