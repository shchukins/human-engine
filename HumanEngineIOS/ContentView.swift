//
//  ContentView.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 05.04.2026.
//

import SwiftUI
import HealthKit

struct ContentView: View {
    @State private var statusMessage = "Not requested"
    @State private var authorizationItems: [(name: String, status: String)] = []

    @State private var weightSamples: [WeightSample] = []
    @State private var restingHRSamples: [RestingHRSample] = []
    @State private var hrvSamples: [HRVSample] = []

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("Human Engine")
                        .font(.largeTitle)
                        .bold()

                    Text("HealthKit integration MVP")
                        .font(.headline)
                        .foregroundStyle(.secondary)

                    GroupBox("Authorization") {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Status: \(statusMessage)")

                            Button("Request permissions") {
                                requestPermissions()
                            }
                            .buttonStyle(.borderedProminent)

                            Button("Refresh statuses") {
                                refreshStatuses()
                            }
                            .buttonStyle(.bordered)

                            Button("Read sample data") {
                                readSampleData()
                            }
                            .buttonStyle(.bordered)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }

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

                    GroupBox("Weight samples") {
                        if weightSamples.isEmpty {
                            Text("No weight samples")
                                .foregroundStyle(.secondary)
                        } else {
                            VStack(alignment: .leading, spacing: 8) {
                                ForEach(weightSamples.prefix(5)) { sample in
                                    Text("\(formatDate(sample.date))  •  \(sample.kilograms, specifier: "%.1f") kg")
                                }
                            }
                        }
                    }

                    GroupBox("Resting HR samples") {
                        if restingHRSamples.isEmpty {
                            Text("No resting HR samples")
                                .foregroundStyle(.secondary)
                        } else {
                            VStack(alignment: .leading, spacing: 8) {
                                ForEach(restingHRSamples.prefix(5)) { sample in
                                    Text("\(formatDate(sample.date))  •  \(sample.bpm, specifier: "%.0f") bpm")
                                }
                            }
                        }
                    }

                    GroupBox("HRV samples") {
                        if hrvSamples.isEmpty {
                            Text("No HRV samples")
                                .foregroundStyle(.secondary)
                        } else {
                            VStack(alignment: .leading, spacing: 8) {
                                ForEach(hrvSamples.prefix(5)) { sample in
                                    Text("\(formatDate(sample.date))  •  \(sample.milliseconds, specifier: "%.1f") ms")
                                }
                            }
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("HealthKit")
            .onAppear {
                refreshStatuses()
            }
        }
    }

    private func requestPermissions() {
        HealthKitService.shared.requestAuthorization { result in
            switch result {
            case .success:
                statusMessage = "Authorization successful"
                refreshStatuses()

            case .failure(let error):
                statusMessage = error.localizedDescription
                refreshStatuses()
            }
        }
    }

    private func refreshStatuses() {
        let statuses = HealthKitService.shared.authorizationStatuses()

        authorizationItems = statuses
            .map { key, value in
                (name: key, status: mapAuthorizationStatus(value))
            }
            .sorted { $0.name < $1.name }
    }

    private func readSampleData() {
        statusMessage = "Reading sample data..."

        HealthKitService.shared.fetchWeightSamplesForLast7Days { weightResult in
            switch weightResult {
            case .success(let weights):
                self.weightSamples = weights
            case .failure(let error):
                self.statusMessage = "Weight read error: \(error.localizedDescription)"
            }
        }

        HealthKitService.shared.fetchRestingHRSamplesForLast7Days { restingHRResult in
            switch restingHRResult {
            case .success(let restingHR):
                self.restingHRSamples = restingHR
            case .failure(let error):
                self.statusMessage = "Resting HR read error: \(error.localizedDescription)"
            }
        }

        HealthKitService.shared.fetchHRVSamplesForLast7Days { hrvResult in
            switch hrvResult {
            case .success(let hrv):
                self.hrvSamples = hrv
                self.statusMessage = "Sample data loaded"
            case .failure(let error):
                self.statusMessage = "HRV read error: \(error.localizedDescription)"
            }
        }
    }

    private func mapAuthorizationStatus(_ status: HKAuthorizationStatus) -> String {
        switch status {
        case .notDetermined:
            return "Not determined"
        case .sharingDenied:
            return "Denied"
        case .sharingAuthorized:
            return "Authorized"
        @unknown default:
            return "Unknown"
        }
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}

#Preview {
    ContentView()
}
