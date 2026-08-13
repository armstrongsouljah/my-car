import { Pressable, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useAuth } from '@/lib/auth-context';

export default function SettingsScreen() {
  const { user, logout } = useAuth();

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.container} edges={['top']}>
        <ThemedText type="title" style={styles.header}>
          Settings
        </ThemedText>

        <ThemedView type="backgroundElement" style={styles.card}>
          <ThemedText type="small" themeColor="textSecondary">
            Signed in as
          </ThemedText>
          <ThemedText type="smallBold">{user?.email}</ThemedText>
        </ThemedView>

        <Pressable onPress={logout} accessibilityRole="button" style={styles.logoutButton}>
          <ThemedText style={styles.logoutText}>Log out</ThemedText>
        </Pressable>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    fontSize: 28,
    paddingHorizontal: Spacing.three,
    paddingTop: Spacing.two,
    paddingBottom: Spacing.three,
  },
  card: {
    marginHorizontal: Spacing.three,
    padding: Spacing.three,
    borderRadius: Spacing.two,
    gap: 2,
    marginBottom: Spacing.four,
  },
  logoutButton: {
    marginHorizontal: Spacing.three,
    borderWidth: 1,
    borderColor: '#DC2626',
    borderRadius: Spacing.two,
    paddingVertical: Spacing.three,
    alignItems: 'center',
  },
  logoutText: {
    color: '#DC2626',
    fontWeight: '600',
  },
});
