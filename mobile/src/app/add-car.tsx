import { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, TextInput } from 'react-native';
import { useRouter } from 'expo-router';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useAuth } from '@/lib/auth-context';
import { useTheme } from '@/hooks/use-theme';

const FUEL_TYPES: { value: string; label: string }[] = [
  { value: 'petrol', label: 'Petrol' },
  { value: 'diesel', label: 'Diesel' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'electric', label: 'Electric' },
];

export default function AddCarScreen() {
  const { apiCall } = useAuth();
  const theme = useTheme();
  const router = useRouter();

  const [make, setMake] = useState('');
  const [model, setModel] = useState('');
  const [year, setYear] = useState('');
  const [registrationNumber, setRegistrationNumber] = useState('');
  const [color, setColor] = useState('');
  const [fuelType, setFuelType] = useState('petrol');
  const [odometerKm, setOdometerKm] = useState('');
  const [vin, setVin] = useState('');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit() {
    setError('');
    setLoading(true);
    try {
      await apiCall('/cars/', {
        method: 'POST',
        body: {
          make: make.trim(),
          model: model.trim(),
          year: year ? Number(year) : null,
          registration_number: registrationNumber,
          color,
          fuel_type: fuelType,
          current_odometer_km: odometerKm ? Number(odometerKm) : 0,
          vin,
          notes,
        },
      });
      router.back(); // Garage tab refetches on focus (see index.tsx's useFocusEffect)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <ThemedView style={styles.container}>
      <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {error ? (
            <ThemedText type="small" style={styles.error}>
              {error}
            </ThemedText>
          ) : null}

          <TextInput
            value={make}
            onChangeText={setMake}
            placeholder="Make (e.g. Toyota)"
            placeholderTextColor={theme.textSecondary}
            style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected }]}
          />
          <TextInput
            value={model}
            onChangeText={setModel}
            placeholder="Model (e.g. Corolla)"
            placeholderTextColor={theme.textSecondary}
            style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected }]}
          />

          <ThemedView style={styles.row}>
            <TextInput
              value={year}
              onChangeText={setYear}
              placeholder="Year"
              placeholderTextColor={theme.textSecondary}
              keyboardType="number-pad"
              style={[styles.input, styles.rowInput, { color: theme.text, borderColor: theme.backgroundSelected }]}
            />
            <TextInput
              value={registrationNumber}
              onChangeText={setRegistrationNumber}
              placeholder="Plate no. (optional)"
              placeholderTextColor={theme.textSecondary}
              autoCapitalize="characters"
              style={[styles.input, styles.rowInput, { color: theme.text, borderColor: theme.backgroundSelected }]}
            />
          </ThemedView>

          <ThemedView style={styles.row}>
            <TextInput
              value={color}
              onChangeText={setColor}
              placeholder="Colour"
              placeholderTextColor={theme.textSecondary}
              style={[styles.input, styles.rowInput, { color: theme.text, borderColor: theme.backgroundSelected }]}
            />
            <TextInput
              value={odometerKm}
              onChangeText={setOdometerKm}
              placeholder="Odometer (km)"
              placeholderTextColor={theme.textSecondary}
              keyboardType="number-pad"
              style={[styles.input, styles.rowInput, { color: theme.text, borderColor: theme.backgroundSelected }]}
            />
          </ThemedView>

          <ThemedText type="small" themeColor="textSecondary" style={styles.label}>
            Fuel
          </ThemedText>
          <ThemedView style={styles.pillRow}>
            {FUEL_TYPES.map((fuel) => {
              const selected = fuel.value === fuelType;
              return (
                <Pressable
                  key={fuel.value}
                  onPress={() => setFuelType(fuel.value)}
                  accessibilityRole="button"
                  style={[
                    styles.pill,
                    {
                      backgroundColor: selected ? theme.brand : theme.backgroundElement,
                      borderColor: selected ? theme.brand : theme.backgroundSelected,
                    },
                  ]}
                >
                  <ThemedText style={selected ? styles.pillTextSelected : undefined}>{fuel.label}</ThemedText>
                </Pressable>
              );
            })}
          </ThemedView>

          <TextInput
            value={vin}
            onChangeText={setVin}
            placeholder="VIN (optional)"
            placeholderTextColor={theme.textSecondary}
            autoCapitalize="characters"
            style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected }]}
          />
          <TextInput
            value={notes}
            onChangeText={setNotes}
            placeholder="Notes (optional)"
            placeholderTextColor={theme.textSecondary}
            multiline
            numberOfLines={3}
            style={[styles.input, styles.notesInput, { color: theme.text, borderColor: theme.backgroundSelected }]}
          />

          <Pressable
            onPress={submit}
            disabled={loading || !make.trim() || !model.trim()}
            accessibilityRole="button"
            style={[
              styles.button,
              { backgroundColor: theme.brand, opacity: loading || !make.trim() || !model.trim() ? 0.6 : 1 },
            ]}
          >
            {loading ? <ActivityIndicator color="#fff" /> : <ThemedText style={styles.buttonText}>Add car</ThemedText>}
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
    padding: Spacing.three,
    gap: Spacing.three,
  },
  error: {
    color: '#DC2626',
    textAlign: 'center',
  },
  row: {
    flexDirection: 'row',
    gap: Spacing.three,
  },
  rowInput: {
    flex: 1,
  },
  input: {
    borderWidth: 1,
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.three,
    fontSize: 16,
  },
  notesInput: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  label: {
    marginBottom: -Spacing.two,
  },
  pillRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  pill: {
    borderWidth: 1,
    borderRadius: Spacing.four,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  pillTextSelected: {
    color: '#fff',
    fontWeight: '600',
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
});
