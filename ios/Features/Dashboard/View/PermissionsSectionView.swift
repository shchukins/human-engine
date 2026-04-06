//
//  PermissionsSectionView.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 06.04.2026.
//

import SwiftUI

struct PermissionsSectionView: View {
    let authorizationItems: [(name: String, status: String)]

    var body: some View {
        GroupBox("Permissions") {
            if authorizationItems.isEmpty {
                Text("No data yet")
                    .foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(authorizationItems, id: \.name) { item in
                        HStack {
                            Text(item.name)
                            Spacer()
                            Text(item.status)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
        }
    }
}

#Preview {
    PermissionsSectionView(
        authorizationItems: [
            (name: "HRV", status: "Authorized"),
            (name: "Sleep", status: "Denied")
        ]
    )
}
