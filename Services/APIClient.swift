//
//  APIClient.swift
//  HumanEngineIOS
//
//  Created by Сергей Щукин on 06.04.2026.
//

import Foundation

final class APIClient {
    static let shared = APIClient()

    private init() {}

    // ВАЖНО: замени на свой реальный endpoint
    private let baseURL = URL(string: "https://api.shchlab.ru")!

    func sendHealthPayload(_ payload: HealthSyncPayload, completion: @escaping (Result<Void, Error>) -> Void) {
        let url = baseURL.appendingPathComponent("/api/v1/healthkit/ingest")

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // временно без auth
        // request.setValue("Bearer YOUR_TOKEN", forHTTPHeaderField: "Authorization")

        let encoder = JSONEncoder()

        do {
            request.httpBody = try encoder.encode(payload)
        } catch {
            completion(.failure(error))
            return
        }

        URLSession.shared.dataTask(with: request) { _, response, error in
            DispatchQueue.main.async {
                if let error {
                    completion(.failure(error))
                    return
                }

                guard let httpResponse = response as? HTTPURLResponse else {
                    completion(.failure(APIError.invalidResponse))
                    return
                }

                if (200...299).contains(httpResponse.statusCode) {
                    completion(.success(()))
                } else {
                    completion(.failure(APIError.serverError(code: httpResponse.statusCode)))
                }
            }
        }.resume()
    }
}

enum APIError: LocalizedError {
    case invalidResponse
    case serverError(code: Int)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid server response"
        case .serverError(let code):
            return "Server error: \(code)"
        }
    }
}
