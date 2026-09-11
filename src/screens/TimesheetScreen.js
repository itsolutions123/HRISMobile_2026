import React, { useState, useEffect, useContext } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, Linking, RefreshControl } from 'react-native';
import { Calendar } from 'react-native-calendars';
import { AuthContext } from '../context/AuthContext';

export default function TimesheetScreen() {
  const { user, API_BASE_URL } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [timesheetData, setTimesheetData] = useState([]);
  const [markedDates, setMarkedDates] = useState({});
  
  const todayStr = new Date().toISOString().split('T')[0];
  const [selectedDate, setSelectedDate] = useState(todayStr);

  const fetchTimesheet = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/timesheet/${user.employee_id}`);
      if (response.ok) {
        const data = await response.json();
        setTimesheetData(data.timesheet || []);

        // Mark calendar dates that contain punches
        let marks = {};
        (data.timesheet || []).forEach((item) => {
          marks[item.date] = {
            marked: true,
            dotColor: '#2563eb',
          };
        });

        // Highlight selected date
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

  return (
    <View style={styles.container}>
      <Text style={styles.headerTitle}>My Timesheet</Text>

      {/* Interactive Calendar Component */}
      <Calendar
        current={selectedDate}
        onDayPress={handleDateSelect}
        markedDates={markedDates}
        theme={{
          todayTextColor: '#2563eb',
          arrowColor: '#2563eb',
          textDayFontWeight: '500',
          textMonthFontWeight: 'bold',
          textDayHeaderFontWeight: '600',
        }}
        style={styles.calendarCard}
      />

      <View style={styles.detailsHeader}>
        <Text style={styles.detailsTitle}>
          {selectedDayRecord ? selectedDayRecord.display_date : selectedDate}
        </Text>
        {selectedDayRecord && (
          <Text style={styles.durationBadge}>Total: {selectedDayRecord.total_duration}</Text>
        )}
      </View>

      {loading ? (
        <ActivityIndicator size="large" color="#2563eb" style={{ marginTop: 20 }} />
      ) : selectedDayRecord && selectedDayRecord.punches.length > 0 ? (
        <FlatList
          data={selectedDayRecord.punches}
          keyExtractor={(item) => item.id.toString()}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchTimesheet(); }} />}
          renderItem={({ item }) => (
            <View style={styles.punchCard}>
              <View style={styles.punchHeader}>
                <Text style={[styles.badge, item.punch_type === 'CLOCK_IN' ? styles.badgeIn : styles.badgeOut]}>
                  {item.punch_type}
                </Text>
                <Text style={styles.punchTime}>{item.time}</Text>
              </View>
              <Text style={styles.address}>📍 {item.address}</Text>

              <TouchableOpacity style={styles.mapBtn} onPress={() => openGoogleMaps(item.lat, item.lng)}>
                <Text style={styles.mapBtnText}>View Location Pin</Text>
              </TouchableOpacity>
            </View>
          )}
        />
      ) : (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No attendance records for this date.</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f8fafc' },
  headerTitle: { fontSize: 22, fontWeight: 'bold', color: '#0f172a', marginBottom: 12 },
  calendarCard: { borderRadius: 12, elevation: 2, borderWidth: 1, borderColor: '#e2e8f0', marginBottom: 16 },
  detailsHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  detailsTitle: { fontSize: 16, fontWeight: 'bold', color: '#1e293b' },
  durationBadge: { backgroundColor: '#1e3a8a', color: '#ffffff', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, fontWeight: 'bold', fontSize: 12 },
  punchCard: { backgroundColor: '#ffffff', padding: 12, borderRadius: 8, marginBottom: 8, borderWidth: 1, borderColor: '#e2e8f0' },
  punchHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  badge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6, fontWeight: 'bold', fontSize: 11, overflow: 'hidden' },
  badgeIn: { backgroundColor: '#dcfce7', color: '#15803d' },
  badgeOut: { backgroundColor: '#fee2e2', color: '#b91c1c' },
  punchTime: { fontSize: 14, fontWeight: 'bold', color: '#334155' },
  address: { fontSize: 12, color: '#64748b', marginBottom: 8 },
  mapBtn: { backgroundColor: '#eff6ff', padding: 6, borderRadius: 6, alignItems: 'center' },
  mapBtnText: { color: '#2563eb', fontWeight: 'bold', fontSize: 12 },
  emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', marginTop: 30 },
  emptyText: { color: '#94a3b8', fontSize: 14 },
});
