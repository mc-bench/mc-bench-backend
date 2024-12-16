module.exports = {
    files: ["**/*.js"],
    languageOptions: {
        ecmaVersion: "latest",
        sourceType: "module"
    },
    linterOptions: {
        reportUnusedDisableDirectives: true,
    },
    rules: {
        // Catch syntax errors and undefined variables
        "no-undef": "error",
        "no-unused-vars": "warn",
        
        // Basic syntax preferences
        "semi": ["error", "always"],
        "no-extra-semi": "warn",
        
        // Common error catches
        "no-unreachable": "error",
        "no-constant-condition": "error",
        "no-dupe-args": "error",
        "no-dupe-keys": "error"
    }
};
