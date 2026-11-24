import AppIntents

struct NovaOpenIntent: AppIntent {
    static var title: LocalizedStringResource = "Open NOVA"
    static var openAppWhenRun = true

    func perform() async throws -> some IntentResult {
        return .result()
    }
}

struct NovaCallMomIntent: AppIntent {
    static var title: LocalizedStringResource = "Ask NOVA to call mom"
    static var openAppWhenRun = true

    func perform() async throws -> some IntentResult {
        return .result()
    }
}

struct NovaShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(intent: NovaOpenIntent(), phrases: ["Open \(.applicationName)"])
        AppShortcut(intent: NovaCallMomIntent(), phrases: ["Ask \(.applicationName) to call mom"])
    }
}
