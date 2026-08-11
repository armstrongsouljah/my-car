import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, Image, StyleSheet, View } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';

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
        <ThemedText type="title" style={styles.header}>
          Your Garage
        </ThemedText>

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
            </ThemedView>
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
  header: {
    fontSize: 28,
    paddingHorizontal: Spacing.three,
    paddingTop: Spacing.two,
    paddingBottom: Spacing.three,
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
