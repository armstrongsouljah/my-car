import { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, TextInput } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useAuth } from '@/lib/auth-context';
import { useTheme } from '@/hooks/use-theme';

export default function LoginScreen() {
  const { login, loginWithGoogle } = useAuth();
  const theme = useTheme();
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
    <ThemedView style={styles.container}>
      <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <ThemedText type="title" style={styles.title}>
          GlavBox
        </ThemedText>
        <ThemedText type="small" themeColor="textSecondary" style={styles.subtitle}>
          Sign in to your garage
        </ThemedText>

        {error ? (
          <ThemedText type="small" style={styles.error}>
            {error}
          </ThemedText>
        ) : null}

        <TextInput
          value={email}
          onChangeText={setEmail}
          placeholder="Email"
          placeholderTextColor={theme.textSecondary}
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected }]}
        />
        <TextInput
          value={password}
          onChangeText={setPassword}
          placeholder="Password"
          placeholderTextColor={theme.textSecondary}
          secureTextEntry
          autoComplete="password"
          style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected }]}
        />

        <Pressable
          onPress={submit}
          disabled={loading || googleLoading || !email || !password}
          accessibilityRole="button"
          style={[styles.button, { backgroundColor: theme.brand, opacity: loading || googleLoading || !email || !password ? 0.6 : 1 }]}
        >
          {loading ? <ActivityIndicator color="#fff" /> : <ThemedText style={styles.buttonText}>Sign in</ThemedText>}
        </Pressable>

        <ThemedView style={styles.dividerRow}>
          <ThemedView style={[styles.dividerLine, { backgroundColor: theme.backgroundSelected }]} />
          <ThemedText type="small" themeColor="textSecondary">or continue with</ThemedText>
          <ThemedView style={[styles.dividerLine, { backgroundColor: theme.backgroundSelected }]} />
        </ThemedView>

        <Pressable
          onPress={submitGoogle}
          disabled={loading || googleLoading}
          accessibilityRole="button"
          style={[styles.googleButton, { borderColor: theme.backgroundSelected, opacity: loading || googleLoading ? 0.6 : 1 }]}
        >
          {googleLoading ? (
            <ActivityIndicator color={theme.text} />
          ) : (
            <ThemedText style={styles.googleButtonText}>Continue with Google</ThemedText>
          )}
        </Pressable>
      </ScrollView>
      </KeyboardAvoidingView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scroll: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: Spacing.four,
    gap: Spacing.three,
  },
  title: {
    textAlign: 'center',
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: Spacing.three,
  },
  error: {
    color: '#DC2626',
    textAlign: 'center',
  },
  input: {
    borderWidth: 1,
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.three,
    fontSize: 16,
  },
  button: {
    borderRadius: Spacing.two,
    paddingVertical: Spacing.three,
    alignItems: 'center',
    marginTop: Spacing.two,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
  },
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    marginTop: Spacing.one,
  },
  dividerLine: {
    flex: 1,
    height: StyleSheet.hairlineWidth,
  },
  googleButton: {
    borderWidth: 1,
    borderRadius: Spacing.two,
    paddingVertical: Spacing.three,
    alignItems: 'center',
  },
  googleButtonText: {
    fontWeight: '600',
  },
});
