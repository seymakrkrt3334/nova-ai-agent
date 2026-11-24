import ExpoModulesCore

public class NovaAssistantModule: Module {
  public func definition() -> ModuleDefinition {
    Name("NovaAssistant")

    AsyncFunction("listen") { () -> [String: String] in
      throw Exception(name: "UNSUPPORTED", description: "iOS uses Siri Shortcuts. Continuous microphone upload is not implemented.")
    }

    AsyncFunction("perform") { (_ request: String) -> [String: Any] in
      return ["ok": false, "detail": "ios-shortcut-required"]
    }
  }
}
