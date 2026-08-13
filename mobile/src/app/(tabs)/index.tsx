import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, Image, Pressable, StyleSheet, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useAuth } from '@/lib/auth-context';
import { mediaUrl } from '@/lib/api';
import { useTheme } from '@/hooks/use-theme';

type Car = {
  id: string;
  make: string;
  model: string;
  year: number | null;
  photo_url: string | null;
  registration_number: string;
  current_odometer_km: number;
};

export default function GarageScreen() {
  const { apiCall } = useAuth();
  const theme = useTheme();
  const router = useRouter();
  const [cars, setCars] = useState<Car[] | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    apiCall('/cars/')
      .then((data) => setCars(data.results || data))
      .catch((err) => setError(err instanceof Error ? err.message : 'Something went wrong'));
  }, [apiCall]);

  // Refetch whenever this tab regains focus (e.g. after adding a car),
  // not just on first mount -- same intent as the web pages' load-on-effect
  // pattern, adapted for a tab navigator where screens stay mounted.
  useFocusEffect(load);

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.container} edges={['top']}>
        <View style={styles.headerRow}>
          <ThemedText type="title" style={styles.headerTitle}>
            Your Garage
          </ThemedText>
          <Pressable
            onPress={() => router.push('/add-car')}
            accessibilityRole="button"
            accessibilityLabel="Add car"
            style={[styles.addButton, { backgroundColor: theme.brand }]}
          >
            <MaterialCommunityIcons name="plus" color="#fff" size={18} />
            <ThemedText style={styles.addButtonText}>Add car</ThemedText>
          </Pressable>
        </View>

        {error ? <ThemedText style={styles.error}>{error}</ThemedText> : null}

        {cars === null && !error && (
          <View style={styles.loading}>
            <ActivityIndicator color={theme.brand} />
          </View>
        )}

        {cars?.length === 0 && (
          <ThemedView type="backgroundElement" style={styles.emptyCard}>
            <ThemedText>No cars yet — add your first one to start tracking services and expenses.</ThemedText>
          </ThemedView>
        )}

        <FlatList
          data={cars ?? []}
          keyExtractor={(car) => car.id}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <Pressable onPress={() => router.push(`/car/${item.id}`)} accessibilityRole="button">
              <ThemedView type="backgroundElement" style={styles.card}>
                {item.photo_url ? (
                  <Image source={{ uri: mediaUrl(item.photo_url) ?? undefined }} style={styles.photo} />
                ) : (
                  <View style={[styles.photo, styles.photoPlaceholder, { backgroundColor: theme.backgroundSelected }]}>
                    <ThemedText type="title">🚗</ThemedText>
                  </View>
                )}
                <View style={styles.cardBody}>
                  <ThemedText type="smallBold">
                    {item.make} {item.model} {item.year ? `(${item.year})` : ''}
                  </ThemedText>
                  <ThemedText type="small" themeColor="textSecondary">
                    {Number(item.current_odometer_km).toLocaleString()} km
                  </ThemedText>
                </View>
                <MaterialCommunityIcons name="chevron-right" color={theme.textSecondary} size={22} />
              </ThemedView>
            </Pressable>
          )}
        />
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.three,
    paddingTop: Spacing.two,
    paddingBottom: Spacing.three,
  },
  headerTitle: {
    fontSize: 28,
  },
  addButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.half,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    borderRadius: Spacing.four,
  },
  addButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  error: {
    color: '#DC2626',
    paddingHorizontal: Spacing.three,
    marginBottom: Spacing.three,
  },
  loading: {
    paddingTop: Spacing.five,
    alignItems: 'center',
  },
  emptyCard: {
    marginHorizontal: Spacing.three,
    padding: Spacing.three,
    borderRadius: Spacing.two,
  },
  list: {
    paddingHorizontal: Spacing.three,
    gap: Spacing.two,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
    padding: Spacing.three,
    borderRadius: Spacing.two,
  },
  photo: {
    width: 56,
    height: 56,
    borderRadius: 28,
  },
  photoPlaceholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardBody: {
    flex: 1,
    gap: 2,
  },
});
