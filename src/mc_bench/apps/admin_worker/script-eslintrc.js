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
        "no-undef": "error",                    // Disallow undeclared variables
        "no-unreachable": "error",              // Disallow unreachable code
        "no-constant-condition": "error",       // Disallow constant conditions in loops/if
        "no-dupe-args": "error",                // Disallow duplicate function parameters
        "no-dupe-keys": "error",                // Disallow duplicate object keys
        "no-dupe-else-if": "error",             // Disallow duplicate conditions in if-else chains
        "no-func-assign": "error",              // Disallow reassigning function declarations
        "no-import-assign": "error",            // Disallow assigning to imported bindings
        "no-obj-calls": "error",                // Disallow calling global objects as functions
        "no-sparse-arrays": "error",            // Disallow sparse arrays with empty slots
        "no-unexpected-multiline": "error",     // Disallow confusing multiline expressions
        "use-isnan": "error",                   // Require using isNaN() to check for NaN
        "valid-typeof": "error"                 // Enforce comparing typeof with valid strings
    }
};
