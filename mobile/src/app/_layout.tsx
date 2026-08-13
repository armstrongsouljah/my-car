import { DarkTheme, DefaultTheme, Stack, ThemeProvider, useRouter, useSegments } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { useColorScheme } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { DancingScript_700Bold, useFonts } from '@expo-google-fonts/dancing-script';

import { AuthProvider, useAuth } from '@/lib/auth-context';

SplashScreen.preventAutoHideAsync();

// Redirects between `(tabs)` and `login` based on session state -- mirrors
// frontend/components/AuthGuard.jsx, but as a layout-level gate (every
// route needs this here, not just page-by-page) since expo-router has no
// per-page wrapper equivalent to Next's per-page component.
function AuthGate({ fontsLoaded }: { fontsLoaded: boolean }) {
  const { user } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (user === undefined || !fontsLoaded) return; // still loading the stored session / brand font

    const inApp = segments[0] === '(tabs)' || segments[0] === 'add-car' || segments[0] === 'car';
    if (!user && inApp) {
      router.replace('/login');
    } else if (user && !inApp) {
      router.replace('/(tabs)');
    }

    SplashScreen.hideAsync();
  }, [user, fontsLoaded, segments, router]);

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="login" />
      <Stack.Screen name="add-car" options={{ headerShown: true, title: 'Add car', presentation: 'modal' }} />
      <Stack.Screen name="car/[id]" options={{ headerShown: true, title: 'Car details' }} />
      <Stack.Screen name="car/[id]/edit" options={{ headerShown: true, title: 'Edit car' }} />
    </Stack>
  );
}

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const [fontsLoaded] = useFonts({ DancingScript_700Bold });

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <AuthProvider>
        <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
          <AuthGate fontsLoaded={fontsLoaded} />
        </ThemeProvider>
      </AuthProvider>
    </GestureHandlerRootView>
  );
}
