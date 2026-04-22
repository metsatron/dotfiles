// OpenCode hooks plugin

// [[file:../../../../hooks.org::*OpenCode hooks plugin][OpenCode hooks plugin:1]]
export const HooksPlugin = async ({ $ }) => {
  return {
    "tui.prompt.append": async () => {
      await $`claude-hook-user-prompt-submit`;
    },
    "session.idle": async () => {
      await $`claude-hook-stop`;
    },
  };
};
// OpenCode hooks plugin:1 ends here
