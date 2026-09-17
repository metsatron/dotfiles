// OpenCode hooks plugin

// [[file:../../../../agents-hooks.org::*OpenCode hooks plugin][OpenCode hooks plugin:1]]
export const HooksPlugin = async ({ $ }) => {
  return {
    "session.idle": async () => {
      await $`claude-hook-stop`;
    },
  };
};
// OpenCode hooks plugin:1 ends here
