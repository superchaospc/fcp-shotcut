import Cocoa

@main
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow!
    private let folderField = NSTextField()
    private let projectField = NSTextField()
    private let eventField = NSTextField()
    private let thresholdSlider = NSSlider(value: 0.35, minValue: 0.15, maxValue: 0.65, target: nil, action: nil)
    private let thresholdLabel = NSTextField(labelWithString: "0.35")
    private let minShotField = NSTextField()
    private let previewsCheck = NSButton(checkboxWithTitle: "Generate cut preview images", target: nil, action: nil)
    private let generateButton = NSButton(title: "Generate Final Cut Pro XML", target: nil, action: nil)
    private let showButton = NSButton(title: "Show Output in Finder", target: nil, action: nil)
    private let statusLabel = NSTextField(labelWithString: "Ready")
    private let logView = NSTextView()

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        buildWindow()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func buildWindow() {
        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 760, height: 560),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "FCP Shotcut"
        window.center()

        let root = NSStackView()
        root.orientation = .vertical
        root.spacing = 14
        root.edgeInsets = NSEdgeInsets(top: 22, left: 22, bottom: 22, right: 22)
        root.translatesAutoresizingMaskIntoConstraints = false

        let title = NSTextField(labelWithString: "FCP Shotcut")
        title.font = NSFont.boldSystemFont(ofSize: 26)
        let subtitle = NSTextField(labelWithString: "Vertical 1080x1920 / 30p / Apple ProRes 422 / Rec.709 / Stereo 48kHz")
        subtitle.textColor = .secondaryLabelColor

        folderField.placeholderString = "/Users/you/Videos/douyin"
        projectField.placeholderString = "Auto-generated if blank"
        eventField.stringValue = "4-16-26"
        minShotField.stringValue = "0.35"
        previewsCheck.state = .on

        thresholdSlider.target = self
        thresholdSlider.action = #selector(thresholdChanged)
        generateButton.target = self
        generateButton.action = #selector(generate)
        showButton.target = self
        showButton.action = #selector(showOutput)

        logView.isEditable = false
        logView.font = NSFont.monospacedSystemFont(ofSize: 12, weight: .regular)
        logView.string = "Choose a folder, then generate timeline.fcpxml.\n"
        let scroll = NSScrollView()
        scroll.hasVerticalScroller = true
        scroll.documentView = logView
        scroll.borderType = .bezelBorder
        scroll.heightAnchor.constraint(greaterThanOrEqualToConstant: 170).isActive = true

        root.addArrangedSubview(title)
        root.addArrangedSubview(subtitle)
        root.addArrangedSubview(row(label: "Video folder", control: folderField, buttonTitle: "Choose...", action: #selector(chooseFolder)))
        root.addArrangedSubview(row(label: "Project name", control: projectField))
        root.addArrangedSubview(twoColumnRow(
            leftLabel: "Event name", leftControl: eventField,
            rightLabel: "Minimum shot length", rightControl: minShotField
        ))
        root.addArrangedSubview(sliderRow())
        root.addArrangedSubview(previewsCheck)
        root.addArrangedSubview(buttonRow())
        root.addArrangedSubview(label("Log"))
        root.addArrangedSubview(scroll)

        window.contentView = NSView()
        window.contentView?.addSubview(root)
        NSLayoutConstraint.activate([
            root.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor),
            root.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor),
            root.topAnchor.constraint(equalTo: window.contentView!.topAnchor),
            root.bottomAnchor.constraint(equalTo: window.contentView!.bottomAnchor)
        ])
    }

    private func label(_ text: String) -> NSTextField {
        let label = NSTextField(labelWithString: text)
        label.font = NSFont.boldSystemFont(ofSize: 13)
        return label
    }

    private func row(label text: String, control: NSControl, buttonTitle: String? = nil, action: Selector? = nil) -> NSView {
        let stack = NSStackView()
        stack.orientation = .horizontal
        stack.spacing = 10
        let lbl = label(text)
        lbl.widthAnchor.constraint(equalToConstant: 120).isActive = true
        control.widthAnchor.constraint(greaterThanOrEqualToConstant: 340).isActive = true
        stack.addArrangedSubview(lbl)
        stack.addArrangedSubview(control)
        if let title = buttonTitle, let action = action {
            let button = NSButton(title: title, target: self, action: action)
            stack.addArrangedSubview(button)
        }
        return stack
    }

    private func twoColumnRow(leftLabel: String, leftControl: NSControl, rightLabel: String, rightControl: NSControl) -> NSView {
        let stack = NSStackView()
        stack.orientation = .horizontal
        stack.spacing = 14
        leftControl.widthAnchor.constraint(equalToConstant: 170).isActive = true
        rightControl.widthAnchor.constraint(equalToConstant: 90).isActive = true
        stack.addArrangedSubview(label(leftLabel))
        stack.addArrangedSubview(leftControl)
        stack.addArrangedSubview(label(rightLabel))
        stack.addArrangedSubview(rightControl)
        return stack
    }

    private func sliderRow() -> NSView {
        let stack = NSStackView()
        stack.orientation = .horizontal
        stack.spacing = 10
        let lbl = label("Scene sensitivity")
        lbl.widthAnchor.constraint(equalToConstant: 120).isActive = true
        thresholdSlider.widthAnchor.constraint(greaterThanOrEqualToConstant: 360).isActive = true
        thresholdLabel.widthAnchor.constraint(equalToConstant: 48).isActive = true
        stack.addArrangedSubview(lbl)
        stack.addArrangedSubview(thresholdSlider)
        stack.addArrangedSubview(thresholdLabel)
        return stack
    }

    private func buttonRow() -> NSView {
        let stack = NSStackView()
        stack.orientation = .horizontal
        stack.spacing = 10
        statusLabel.textColor = .secondaryLabelColor
        stack.addArrangedSubview(generateButton)
        stack.addArrangedSubview(showButton)
        stack.addArrangedSubview(statusLabel)
        return stack
    }

    @objc private func thresholdChanged() {
        thresholdLabel.stringValue = String(format: "%.2f", thresholdSlider.doubleValue)
    }

    @objc private func chooseFolder() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        panel.message = "Choose a folder with videos"
        if panel.runModal() == .OK, let url = panel.url {
            folderField.stringValue = url.path
        }
    }

    @objc private func generate() {
        let folder = folderField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !folder.isEmpty, FileManager.default.fileExists(atPath: folder) else {
            alert("Please choose a valid video folder.")
            return
        }

        let resources = Bundle.main.resourceURL!
        let cli = resources.appendingPathComponent("fcp_shotcut.py").path
        var args = [
            cli,
            folder,
            "--event-name", eventField.stringValue.isEmpty ? "4-16-26" : eventField.stringValue,
            "--threshold", String(format: "%.3f", thresholdSlider.doubleValue),
            "--min-shot-len", minShotField.stringValue.isEmpty ? "0.35" : minShotField.stringValue
        ]
        let project = projectField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        if !project.isEmpty {
            args.append(contentsOf: ["--project-name", project])
        }
        if previewsCheck.state != .on {
            args.append("--no-previews")
        }

        generateButton.isEnabled = false
        statusLabel.stringValue = "Generating..."
        logView.string = ""

        DispatchQueue.global(qos: .userInitiated).async {
            let output = self.runPython(args: args)
            DispatchQueue.main.async {
                self.logView.string = output.text
                self.generateButton.isEnabled = true
                self.statusLabel.stringValue = output.ok ? "Done" : "Failed"
                if !output.ok {
                    self.alert("Generation failed. Check the log.")
                }
            }
        }
    }

    private func runPython(args: [String]) -> (ok: Bool, text: String) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3"] + args
        var environment = ProcessInfo.processInfo.environment
        environment["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        process.environment = environment
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        do {
            try process.run()
            process.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            return (process.terminationStatus == 0, String(data: data, encoding: .utf8) ?? "")
        } catch {
            return (false, "Could not run python3. Install Python 3 and ffmpeg, then try again.\n\n\(error)")
        }
    }

    @objc private func showOutput() {
        let folder = folderField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !folder.isEmpty else { return }
        let edit = URL(fileURLWithPath: folder).appendingPathComponent("edit")
        let target = FileManager.default.fileExists(atPath: edit.path) ? edit : URL(fileURLWithPath: folder)
        NSWorkspace.shared.open(target)
    }

    private func alert(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "FCP Shotcut"
        alert.informativeText = message
        alert.runModal()
    }
}
