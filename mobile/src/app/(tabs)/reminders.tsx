import { StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';

// Placeholder -- the Garage tab (index.tsx) is this app's first real,
// API-wired screen. This and expenses.tsx are next up.
export default function RemindersScreen() {
  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.container} edges={['top']}>
        <ThemedText type="title" style={styles.header}>
          Reminders
        </ThemedText>
        <ThemedText themeColor="textSecondary" style={styles.body}>
          Coming soon.
        </ThemedText>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    fontSize: 28,
    paddingHorizontal: Spacing.three,
    paddingTop: Spacing.two,
    paddingBottom: Spacing.three,
  },
  body: {
    paddingHorizontal: Spacing.three,
  },
});
