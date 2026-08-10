module.exports = [
  {
    files: ["eslint.config.js"],
    languageOptions: {
      sourceType: "commonjs",
      globals: {
        module: "readonly", require: "readonly", process: "readonly",
        __dirname: "readonly", __filename: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "error",
    },
  },
  {
    files: ["**/*.{js,jsx}"],
    ignores: ["**/node_modules/**", "**/dist/**", "**/build/**", "**/__pycache__/**", "**/*.py", "**/*.json", "eslint.config.js"],
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
      "no-undef": "error",
      "no-unused-vars": "error",
    },
  },
];
