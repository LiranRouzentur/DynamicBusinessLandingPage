/**
 * Development-only console logger
 * In production builds, these calls are stripped out
 */

const isDev = import.meta.env.DEV;

export const logger = {
  log: (...args: any[]) => {
    if (isDev) console.log(...args);
  },
  warn: (...args: any[]) => {
    if (isDev) console.warn(...args);
  },
  error: (...args: any[]) => {
    if (isDev) console.error(...args);
  },
  info: (...args: any[]) => {
    if (isDev) console.info(...args);
  },
};

