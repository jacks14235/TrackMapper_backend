//
//  APIService.swift
//  TrackMapper
//
//  Created by Arnav Nayak on 4/15/25 with help from ChatGPT.
//

import Foundation
import SwiftUI

final class APIService {
    static let shared = APIService() // singleton
    
    private let baseURL = "http://vcm-47369.vm.duke.edu:8080"
    
    // fetches all map posts from the backend.
    func fetchMaps(completion: @escaping (Result<[DBMapObject], Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/maps") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        URLSession.shared.dataTask(with: url) { data, _, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            guard let data = data else {
                completion(.failure(APIError.noData))
                return
            }
            do {
                let decoder = JSONDecoder()
                decoder.dateDecodingStrategy = .iso8601
                let maps = try decoder.decode([MapPost].self, from: data)
                completion(.success(maps))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }

    // authenticates a user by sending their username and password.
    func login(username: String, password: String, completion: @escaping (Result<UserProfile, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/users/login") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let credentials = ["username": username, "password": password]
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            let jsonData = try JSONSerialization.data(withJSONObject: credentials, options: [])
            request.httpBody = jsonData
        } catch {
            completion(.failure(error))
            return
        }
        
        URLSession.shared.dataTask(with: request) { data, _, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            guard let data = data else {
                completion(.failure(APIError.noData))
                return
            }
            do {
                let decoder = JSONDecoder()
                let user = try decoder.decode(UserProfile.self, from: data)
                completion(.success(user))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
    
    // registers a new user with the provided information.
    func register(name: String, username: String, password: String, completion: @escaping (Result<UserProfile, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/users") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let userData = ["name": name, "username": username, "password": password]
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            let jsonData = try JSONSerialization.data(withJSONObject: userData, options: [])
            request.httpBody = jsonData
        } catch {
            completion(.failure(error))
            return
        }
        
        URLSession.shared.dataTask(with: request) { data, _, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            guard let data = data else {
                completion(.failure(APIError.noData))
                return
            }
            do {
                let decoder = JSONDecoder()
                let user = try decoder.decode(UserProfile.self, from: data)
                completion(.success(user))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
    
    // fetches the profile for a specific user.
    func fetchUserProfile(userID: String, completion: @escaping (Result<UserProfile, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/users") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        URLSession.shared.dataTask(with: url) { data, _, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            guard let data = data else {
                completion(.failure(APIError.noData))
                return
            }
            do {
                let decoder = JSONDecoder()
                let users = try decoder.decode([UserProfile].self, from: data)
                if let user = users.first(where: { $0.id.uuidString == userID }) {
                    completion(.success(user))
                } else {
                    completion(.failure(APIError.userNotFound))
                }
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
    
    // updates the profile for a specific user.
    func updateUserProfile(userID: String, updatedData: [String: String], completion: @escaping (Result<Void, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/users/\(userID)") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "PATCH"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            let jsonData = try JSONSerialization.data(withJSONObject: updatedData, options: [])
            request.httpBody = jsonData
        } catch {
            completion(.failure(error))
            return
        }
        
        URLSession.shared.dataTask(with: request) { _, _, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            completion(.success(()))
        }.resume()
    }
    
    // fetches all maps for a user
    func fetchUserMaps(userID: String, completion: @escaping (Result<[MapPost], Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/maps/user?userID=\(userID)") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        URLSession.shared.dataTask(with: url) { data, _, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            guard let data = data else {
                completion(.failure(APIError.noData))
                return
            }
            do {
                let decoder = JSONDecoder()
                decoder.dateDecodingStrategy = .iso8601
                let maps = try decoder.decode([MapPost].self, from: data)
                completion(.success(maps))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
    
    // deletes a map post for a user
    func deleteMapPost(mapID: UUID, completion: @escaping (Result<Void, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/maps/\(mapID)") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        URLSession.shared.dataTask(with: request) { _, _, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            completion(.success(()))
        }.resume()
    }
    
    // creates a map post for a user
    func createMapPost(image: UIImage, title: String, description: String, spline: Spline, completion: @escaping (Result<MapPost, Error>) -> Void) {
        guard let imgData = image.pngData() else {
            completion(.failure(APIError.imageConversionFailed))
            return
        }
        let base64String = imgData.base64EncodedString()
        
        guard let userID = SessionManager.shared.currentUser?.id.uuidString else {
            completion(.failure(APIError.notLoggedIn))
            return
        }
        
        let pairs = spline.getPairs().map { localPair in
            return [
                "real": ["x": localPair.real.x, "y": localPair.real.y],
                "map":  ["x": localPair.map.x,  "y": localPair.map.y]
            ]
        }
        
        let payload: [String: Any] = [
            "imageData": base64String,
            "title": title,
            "description": description,
            "userID": userID,
            "centerX":    spline.getCenter().x,
            "centerY":    spline.getCenter().y,
            "N":          spline.m,
            "pairs":      pairs
        ]
        
        guard let jsonData = try? JSONSerialization.data(withJSONObject: payload) else {
            completion(.failure(APIError.jsonSerializationFailed))
            return
        }
        
        guard let url = URL(string: "\(baseURL)/maps") else {
            completion(.failure(APIError.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = jsonData
        
        URLSession.shared.dataTask(with: request) { data, _, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            guard let data = data else {
                completion(.failure(APIError.noData))
                return
            }
            do {
                let decoder = JSONDecoder()
                decoder.dateDecodingStrategy = .iso8601
                let mapPost = try decoder.decode(MapPost.self, from: data)
                completion(.success(mapPost))
            } catch {
                debugPrint(error)
                if let raw = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    var jsonObject = raw
                    if let base64 = jsonObject["imageData"] as? String {
                      jsonObject["imageData"] = "…\(base64.count) bytes omitted…"
                    }
                    if
                      let filtered = try? JSONSerialization.data(withJSONObject: jsonObject, options: .prettyPrinted),
                      let filteredString = String(data: filtered, encoding: .utf8)
                    {
                      print("→ Response JSON (filtered):\n\(filteredString)")
                    }
                }
                completion(.failure(error))
            }
        }.resume()
    }
}

extension APIService {

    // uploads track for user
    func uploadTrack(gpx xml: String,
                     mapID: UUID?,
                     completion: @escaping (Result<TrackPost,Error>) -> Void)
    {
        guard let uid = SessionManager.shared.currentUser?.id.uuidString else {
            completion(.failure(APIError.notLoggedIn)); return
        }
        guard let url = URL(string: "\(baseURL)/tracks") else {
            completion(.failure(APIError.invalidURL)); return
        }

        let payload: [String: Any?] = [
            "userID":  uid,
            "mapID":   mapID?.uuidString,
            "gpxData": xml
        ]

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: payload.compactMapValues { $0 })

        URLSession.shared.dataTask(with: request) { data,_,err in
            if let err = err { completion(.failure(err)); return }
            guard let data = data else { completion(.failure(APIError.noData)); return }
            do {
                let decoder = JSONDecoder(); decoder.dateDecodingStrategy = .iso8601
                let track = try decoder.decode(TrackPost.self, from: data)
                completion(.success(track))
            } catch {
                debugPrint(error)
                if let raw = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    let jsonObject = raw
                    if
                      let filtered = try? JSONSerialization.data(withJSONObject: jsonObject, options: .prettyPrinted),
                      let filteredString = String(data: filtered, encoding: .utf8)
                    {
                      print("→ Response JSON (filtered):\n\(filteredString)")
                    }
                }
                completion(.failure(error))
            }
        }.resume()
    }

    // fetches user's tracks
    func fetchUserTracks(userID: String,
                         completion: @escaping (Result<[TrackPost],Error>) -> Void)
    {
        guard let url = URL(string: "\(baseURL)/tracks/user?userID=\(userID)") else {
            completion(.failure(APIError.invalidURL)); return
        }
        URLSession.shared.dataTask(with: url) { data,_,err in
            if let err = err { completion(.failure(err)); return }
            guard let data = data else { completion(.failure(APIError.noData)); return }
            do {
                let dec = JSONDecoder(); dec.dateDecodingStrategy = .iso8601
                let tracks = try dec.decode([TrackPost].self, from: data)
                completion(.success(tracks))
            } catch { completion(.failure(error)) }
        }.resume()
    }

    // deletes user's tracks
    func deleteTrack(trackID: UUID, completion: @escaping (Result<Void,Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/tracks/\(trackID)") else {
            completion(.failure(APIError.invalidURL)); return
        }
        var req = URLRequest(url: url); req.httpMethod = "DELETE"
        URLSession.shared.dataTask(with: req) { _,_,err in
            if let err = err { completion(.failure(err)) }
            else           { completion(.success(()))    }
        }.resume()
    }
}


// APIService Errors
enum APIError: Error, LocalizedError {
    case invalidURL, noData, imageConversionFailed, notLoggedIn, jsonSerializationFailed, userNotFound
    
    var errorDescription: String? {
        switch self {
        case .userNotFound:
            return "User not found."
        case .invalidURL:
            return "The URL provided was invalid."
        case .noData:
            return "No data was received from the server."
        case .imageConversionFailed:
            return "Failed to convert image."
        case .notLoggedIn:
            return "User is not logged in."
        case .jsonSerializationFailed:
            return "Failed to serialize JSON."
        }
    }
}


struct DBMapObject: Codable, Identifiable {
    let id: UUID
    let title: String
    let description: String
    let imageURL: String
    let metaURL: String
    let userId: Int
    let latitude: Double
    let longitude: Double
    let uploadedAt: Date
}
