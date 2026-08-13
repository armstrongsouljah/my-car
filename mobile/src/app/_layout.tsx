import { DarkTheme, DefaultTheme, Stack, ThemeProvider, useRouter, useSegments } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { useColorScheme } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import { AuthProvider, useAuth } from '@/lib/auth-context';

SplashScreen.preventAutoHideAsync();

// Redirects between `(tabs)` and `login` based on session state -- mirrors
// frontend/components/AuthGuard.jsx, but as a layout-level gate (every
// route needs this here, not just page-by-page) since expo-router has no
// per-page wrapper equivalent to Next's per-page component.
function AuthGate() {
  const { user } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (user === undefined) return; // still loading the stored session

    const inTabs = segments[0] === '(tabs)';
    if (!user && inTabs) {
      router.replace('/login');
    } else if (user && !inTabs) {
      router.replace('/(tabs)');
    }

    SplashScreen.hideAsync();
  }, [user, segments, router]);

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="login" />
    </Stack>
  );
}

export default function RootLayout() {
  const colorScheme = useColorScheme();
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <AuthProvider>
        <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
          <AuthGate />
        </ThemeProvider>
      </AuthProvider>
    </GestureHandlerRootView>
  );
}
