module.exports = [
  {
    ignores: ["**/node_modules/**", "**/dist/**", "**/build/**", "**/__pycache__/**", "**/*.py", "**/*.json"],
    languageOptions: {
      sourceType: "module",
      globals: {
        window: "readonly", document: "readonly", fetch: "readonly", console: "readonly",
        localStorage: "readonly", setInterval: "readonly", clearInterval: "readonly",
        setTimeout: "readonly", clearTimeout: "readonly", location: "readonly",
        navigator: "readonly", alert: "readonly", confirm: "readonly", prompt: "readonly",
        CustomEvent: "readonly", HTMLElement: "readonly", Event: "readonly",
        WebSocket: "readonly", URL: "readonly", performance: "readonly",
        requestAnimationFrame: "readonly", EventSource: "readonly", atob: "readonly",
      },
    },
    rules: {
      "no-undef": "off",
      "no-unused-vars": "off",
    },
  },
];
