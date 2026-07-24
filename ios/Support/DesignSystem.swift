import SwiftUI

enum WhatteColors {
    static let background = Color(red: 10 / 255, green: 10 / 255, blue: 10 / 255)
    static let card = Color(red: 19 / 255, green: 21 / 255, blue: 22 / 255)
    static let cardSecondary = Color(red: 24 / 255, green: 26 / 255, blue: 27 / 255)
    static let border = Color(red: 48 / 255, green: 52 / 255, blue: 54 / 255)
    static let primaryText = Color(red: 243 / 255, green: 240 / 255, blue: 232 / 255)
    static let secondaryText = Color(red: 139 / 255, green: 145 / 255, blue: 149 / 255)
    static let accentGreen = Color(red: 200 / 255, green: 1.0, blue: 46 / 255)
    static let accentCyan = Color(red: 85 / 255, green: 214 / 255, blue: 1.0)
    static let accentYellow = Color(red: 1.0, green: 211 / 255, blue: 90 / 255)
    static let error = Color(red: 1.0, green: 96 / 255, blue: 122 / 255)
}

enum HEColor {
    static let background = WhatteColors.background
    static let card = WhatteColors.card
    static let cardSecondary = WhatteColors.cardSecondary
    static let border = WhatteColors.border
    static let primaryText = WhatteColors.primaryText
    static let secondaryText = WhatteColors.secondaryText
    static let accentGreen = WhatteColors.accentGreen
    static let accentCyan = WhatteColors.accentCyan
    static let accentYellow = WhatteColors.accentYellow
    static let error = WhatteColors.error
}

enum HETypography {
    static let overline = Font.system(size: 11, weight: .medium, design: .monospaced)
    static let metric = Font.system(size: 15, weight: .semibold, design: .default)
    static let value = Font.system(size: 22, weight: .semibold, design: .default)
    static let hero = Font.system(size: 38, weight: .black, design: .default)
    static let title = Font.system(size: 18, weight: .bold, design: .default)
    static let body = Font.system(size: 15, weight: .regular, design: .default)
    static let status = Font.system(size: 34, weight: .bold, design: .default)
}

struct HECardModifier: ViewModifier {
    let background: Color

    func body(content: Content) -> some View {
        content
            .padding(18)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(background)
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(HEColor.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .shadow(color: .black.opacity(0.18), radius: 18, y: 8)
    }
}

extension View {
    func heCard(background: Color = HEColor.card) -> some View {
        modifier(HECardModifier(background: background))
    }
}
