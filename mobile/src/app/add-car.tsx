import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';

import { CarForm } from '@/components/car-form';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';

export default function AddCarScreen() {
  const router = useRouter();

  return (
    <ThemedView style={styles.container}>
      <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {/* Garage tab refetches on focus (see (tabs)/index.tsx's useFocusEffect) */}
          <CarForm onSaved={() => router.back()} />
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
    padding: Spacing.three,
  },
});
