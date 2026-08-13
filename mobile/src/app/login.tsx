import { useState } from 'react';
import { ActivityIndicator, Image, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useAuth } from '@/lib/auth-context';

// Always dark, regardless of system theme -- mirrors frontend/app/login/
// page.jsx, which hardcodes the same #04120c/#0a1a14 palette unconditionally
// rather than following next-themes like the rest of the web app does.
const BG = '#04120c';
const SHEET_BG = '#0a1a14';
const HERO_IMAGE =
  'https://res.cloudinary.com/soultech/image/upload/e_improve,w_900,h_700,c_fill,g_auto,q_auto,f_auto/v1784111131/MANSORY_P1100_Audi_RS6_Carbon_Turquoise_Madness_Part_2_zos9uq.jpg';

export default function LoginScreen() {
  const { login, loginWithGoogle } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  async function submit() {
    setError('');
    setLoading(true);
    try {
      await login(email.trim(), password);
      // Navigation on success is handled by AuthGate (see app/_layout.tsx)
      // reacting to the user state change -- nothing to do here.
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  async function submitGoogle() {
    setError('');
    setGoogleLoading(true);
    try {
      await loginWithGoogle();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setGoogleLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled" bounces={false}>
        <Image source={{ uri: HERO_IMAGE }} style={styles.hero} />
        <LinearGradient colors={['transparent', 'rgba(4,18,12,0.2)', BG]} style={styles.heroBottomFade} />
        <LinearGradient colors={['rgba(0,0,0,0.8)', 'rgba(0,0,0,0.4)', 'transparent']} style={styles.heroTopFade} />
        <ThemedText style={styles.brand}>GlavBox</ThemedText>
        <ThemedText style={styles.tagline}>Welcome back to your garage</ThemedText>

        <View style={styles.sheet}>
          {error ? <ThemedText style={styles.error}>{error}</ThemedText> : null}

          <TextInput
            value={email}
            onChangeText={setEmail}
            placeholder="Email address"
            placeholderTextColor="rgba(255,255,255,0.3)"
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            style={styles.input}
          />
          <TextInput
            value={password}
            onChangeText={setPassword}
            placeholder="Password"
            placeholderTextColor="rgba(255,255,255,0.3)"
            secureTextEntry
            autoComplete="password"
            style={styles.input}
          />

          <Pressable onPress={submit} disabled={loading || googleLoading || !email || !password} accessibilityRole="button">
            <LinearGradient
              colors={['#34D399', '#22C55E']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={[styles.button, { opacity: loading || googleLoading || !email || !password ? 0.5 : 1 }]}
            >
              {loading ? <ActivityIndicator color={BG} /> : <ThemedText style={styles.buttonText}>Sign in</ThemedText>}
            </LinearGradient>
          </Pressable>

          <View style={styles.dividerRow}>
            <View style={styles.dividerLine} />
            <ThemedText style={styles.dividerText}>or continue with</ThemedText>
            <View style={styles.dividerLine} />
          </View>

          <Pressable
            onPress={submitGoogle}
            disabled={loading || googleLoading}
            accessibilityRole="button"
            style={[styles.googleButton, { opacity: loading || googleLoading ? 0.5 : 1 }]}
          >
            {googleLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <ThemedText numberOfLines={1} style={styles.googleButtonText}>
                Continue with Google
              </ThemedText>
            )}
          </Pressable>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: BG,
  },
  scroll: {
    flexGrow: 1,
  },
  hero: {
    width: '100%',
    height: 280,
  },
  heroBottomFade: {
    position: 'absolute',
    top: 140,
    left: 0,
    right: 0,
    height: 140,
  },
  heroTopFade: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 100,
  },
  brand: {
    position: 'absolute',
    top: 44,
    left: 0,
    right: 0,
    textAlign: 'center',
    fontFamily: 'DancingScript_700Bold',
    fontSize: 40,
    lineHeight: 48,
    color: '#fff',
    textShadowColor: 'rgba(0,0,0,0.9)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 10,
  },
  tagline: {
    position: 'absolute',
    top: 92,
    left: 0,
    right: 0,
    textAlign: 'center',
    fontSize: 14,
    color: 'rgba(209,250,229,0.8)',
    textShadowColor: 'rgba(0,0,0,0.9)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 6,
  },
  sheet: {
    flex: 1,
    marginTop: -32,
    backgroundColor: SHEET_BG,
    borderTopLeftRadius: 32,
    borderTopRightRadius: 32,
    paddingHorizontal: Spacing.four,
    paddingTop: Spacing.four,
    paddingBottom: Spacing.five,
    gap: Spacing.three,
  },
  error: {
    color: '#fca5a5',
    backgroundColor: 'rgba(248,113,113,0.1)',
    borderRadius: Spacing.three,
    padding: Spacing.three,
    fontSize: 14,
    textAlign: 'center',
  },
  input: {
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 16,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.three,
    fontSize: 15,
    color: '#fff',
  },
  button: {
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: Spacing.two,
    shadowColor: '#34D399',
    shadowOpacity: 0.35,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 8 },
  },
  buttonText: {
    color: BG,
    fontWeight: '700',
    fontSize: 15,
  },
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    marginTop: Spacing.two,
  },
  dividerLine: {
    flex: 1,
    height: StyleSheet.hairlineWidth,
    backgroundColor: 'rgba(255,255,255,0.1)',
  },
  dividerText: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.3)',
  },
  googleButton: {
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: 'center',
  },
  googleButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 15,
  },
});
