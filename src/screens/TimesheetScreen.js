import React, { useState, useEffect, useContext } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, Linking, RefreshControl, Platform } from 'react-native';
import { Calendar } from 'react-native-calendars';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function TimesheetScreen() {
  const { user, API_BASE_URL } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [timesheetData, setTimesheetData] = useState([]);
  const [allPunches, setAllPunches] = useState([]);
  const [markedDates, setMarkedDates] = useState({});
  
  const getLocalDateString = (d = new Date()) => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const [selectedDate, setSelectedDate] = useState(getLocalDateString());

  const fetchTimesheet = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/timesheet/${user.employee_id}`);
      if (response.ok) {
        const data = await response.json();
        const history = data.timesheet || [];
        const rawPunches = data.all_punches || [];

        setTimesheetData(history);
        setAllPunches(rawPunches);

        let marks = {};
        history.forEach((item) => {
          marks[item.date] = {
            marked: true,
            dotColor: '#2563eb',
          };
        });

        marks[selectedDate] = {
          ...(marks[selectedDate] || {}),
          selected: true,
          selectedColor: '#2563eb',
        };

        setMarkedDates(marks);
      }
    } catch (error) {
      console.log('Error fetching timesheet:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchTimesheet();
  }, []);

  const handleDateSelect = (day) => {
    const dateStr = day.dateString;
    setSelectedDate(dateStr);

    let updatedMarks = { ...markedDates };
    Object.keys(updatedMarks).forEach((key) => {
      if (updatedMarks[key].selected) {
        delete updatedMarks[key].selected;
        delete updatedMarks[key].selectedColor;
      }
    });

    updatedMarks[dateStr] = {
      ...(updatedMarks[dateStr] || {}),
      selected: true,
      selectedColor: '#2563eb',
    };

    setMarkedDates(updatedMarks);
  };

  const openGoogleMaps = (lat, lng) => {
    const url = `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
    Linking.openURL(url);
  };

  const selectedDayRecord = timesheetData.find((item) => item.date === selectedDate);
  const displayList = selectedDayRecord ? selectedDayRecord.punches : allPunches;

  return (
    <View style={styles.container}>
      {/* Calendar Card Widget */}
      <View style={styles.calendarCardContainer}>
        <Calendar
          current={selectedDate}
          onDayPress={handleDateSelect}
          markedDates={markedDates}
          theme={{
            calendarBackground: '#ffffff',
            textSectionTitleColor: '#94a3b8',
            selectedDayBackgroundColor: '#2563eb',
            selectedDayTextColor: '#ffffff',
            todayTextColor: '#2563eb',
            dayTextColor: '#1e293b',
            textDisabledColor: '#cbd5e1',
            dotColor: '#2563eb',
            selectedDotColor: '#ffffff',
            arrowColor: '#2563eb',
            monthTextColor: '#0f172a',
            indicatorColor: '#2563eb',
            textDayFontWeight: '600',
            textMonthFontWeight: '700',
            textDayHeaderFontWeight: '600',
            textDayFontSize: 14,
            textMonthFontSize: 16,
            textDayHeaderFontSize: 12,
          }}
        />
      </View>

      {/* Date Header Summary Card */}
      <View style={styles.summaryBar}>
        <View style={styles.summaryLeft}>
          <Ionicons name="calendar-outline" size={18} color="#2563eb" />
          <Text style={styles.summaryTitle}>
            {selectedDayRecord ? selectedDayRecord.display_date : `Recent Log History`}
          </Text>
        </View>
        {selectedDayRecord && (
          <View style={styles.durationPill}>
            <Ionicons name="time-outline" size={13} color="#ffffff" style={{ marginRight: 4 }} />
            <Text style={styles.durationText}>{selectedDayRecord.total_duration}</Text>
          </View>
        )}
      </View>

      {/* Punch Feed List */}
      {loading ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#2563eb" />
        </View>
      ) : displayList.length > 0 ? (
        <FlatList
          data={displayList}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={{ paddingBottom: 20 }}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchTimesheet(); }} tintColor="#2563eb" />
          }
          renderItem={({ item }) => {
            const isClockIn = item.punch_type === 'CLOCK_IN';
            return (
              <View style={styles.punchCard}>
                <View style={styles.cardTopRow}>
                  <View style={[styles.statusBadge, isClockIn ? styles.badgeIn : styles.badgeOut]}>
                    <Ionicons 
                      name={isClockIn ? "arrow-down-circle-outline" : "arrow-up-circle-outline"} 
                      size={14} 
                      color={isClockIn ? "#166534" : "#991b1b"} 
                    />
                    <Text style={[styles.statusBadgeText, isClockIn ? styles.textIn : styles.textOut]}>
                      {isClockIn ? 'CLOCK IN' : 'CLOCK OUT'}
                    </Text>
                  </View>

                  <Text style={styles.timestampText}>{item.time}</Text>
                </View>

                <View style={styles.locationRow}>
                  <Ionicons name="location-sharp" size={15} color="#64748b" style={{ marginRight: 4 }} />
                  <Text style={styles.addressText} numberOfLines={1}>{item.address}</Text>
                </View>

                <TouchableOpacity 
                  style={styles.mapActionChip} 
                  activeOpacity={0.7} 
                  onPress={() => openGoogleMaps(item.lat, item.lng)}
                >
                  <Ionicons name="map-outline" size={14} color="#2563eb" />
                  <Text style={styles.mapActionText}>View Location Pin</Text>
                </TouchableOpacity>
              </View>
            );
          }}
        />
      ) : (
        <View style={styles.emptyContainer}>
          <Ionicons name="document-text-outline" size={48} color="#cbd5e1" />
          <Text style={styles.emptyText}>No attendance records found for this date.</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f8fafc' },
  calendarCardContainer: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    overflow: 'hidden',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    ...Platform.select({
      ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 8 },
      android: { elevation: 3 },
    }),
  },
  summaryBar: {
    flexDirection: 'row',
    justify: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
    paddingHorizontal: 4,
  },
  summaryLeft: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  summaryTitle: { fontSize: 15, fontWeight: '700', color: '#0f172a' },
  durationPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2563eb',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
  },
  durationText: { color: '#ffffff', fontWeight: '700', fontSize: 12 },
  punchCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    ...Platform.select({
      ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 4 },
      android: { elevation: 2 },
    }),
  },
  cardTopRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  badgeIn: { backgroundColor: '#f0fdf4', borderWidth: 1, borderColor: '#bbf7d0' },
  badgeOut: { backgroundColor: '#fef2f2', borderWidth: 1, borderColor: '#fecaca' },
  statusBadgeText: { fontWeight: '700', fontSize: 11, letterSpacing: 0.3 },
  textIn: { color: '#166534' },
  textOut: { color: '#991b1b' },
  timestampText: { fontSize: 13, fontWeight: '700', color: '#334155', fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace' },
  locationRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  addressText: { fontSize: 13, color: '#64748b', flex: 1 },
  mapActionChip: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: '#eff6ff',
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#dbeafe',
  },
  mapActionText: { color: '#2563eb', fontWeight: '600', fontSize: 12 },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', marginTop: 40, gap: 8 },
  emptyText: { color: '#94a3b8', fontSize: 14, fontWeight: '500' },
});
