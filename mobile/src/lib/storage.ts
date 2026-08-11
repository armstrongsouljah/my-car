import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

// expo-secure-store (Keychain/Keystore) has no web implementation -- it
// throws outright when called there. Web is a real, if secondary, target
// for this app (see app.json's "web" config), so this falls back to
// localStorage on that platform specifically, wrapped in the same async
// interface SecureStore already exposes on native. Not meant as a "secure"
// store on web (localStorage never is) -- just parity so the app doesn't
// hard-crash there.
export async function getItem(key: string): Promise<string | null> {
  if (Platform.OS === 'web') return localStorage.getItem(key);
  return SecureStore.getItemAsync(key);
}

export async function setItem(key: string, value: string): Promise<void> {
  if (Platform.OS === 'web') {
    localStorage.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

export async function deleteItem(key: string): Promise<void> {
  if (Platform.OS === 'web') {
    localStorage.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}
