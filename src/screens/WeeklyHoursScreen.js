import React, { useState, useEffect, useContext } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function WeeklyHoursScreen() {
  const { user, token, API_BASE_URL } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [cutoffDays, setCutoffDays] = useState([]);
  const [punches, setPunches] = useState([]);
  const [periodLabel, setPeriodLabel] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const today = new Date();
      const year = today.getFullYear();
      const month = today.getMonth();
      const date = today.getDate();

      let startDate, endDate;
      if (date <= 15) {
        startDate = new Date(year, month, 1);
        endDate = new Date(year, month, 15);
        setPeriodLabel(`1st - 15th, ${today.toLocaleString('default', { month: 'long', year: 'numeric' })}`);
      } else {
        startDate = new Date(year, month, 16);
        endDate = new Date(year, month + 1, 0); // Last day of month
        setPeriodLabel(`16th - End of Month, ${today.toLocaleString('default', { month: 'long', year: 'numeric' })}`);
      }

      const days = [];
      for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
        days.push(new Date(d).toISOString().split('T')[0]);
      }
      setCutoffDays(days.reverse()); // Show newest first

      const logsRes = await fetch(`${API_BASE_URL}/api/punch/my-logs`, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (logsRes.ok) {
        const logs = await logsRes.json();
        setPunches(logs.filter(p => p.employee_id === user?.employee_id));
      }
    } catch (error) {
      console.log('Error fetching weekly hours:', error);
    } finally {
      setLoading(false);
    }
  };

  const normalizeDate = (ts) => {
    if (!ts) return '';
    if (ts.includes('T')) return ts.split('T')[0];
    if (ts.includes(',')) {
      const parts = ts.split(',')[0].split('/');
      if (parts.length === 3) return `${parts[2]}-${parts[0].padStart(2, '0')}-${parts[1].padStart(2, '0')}`;
    }
    const first = ts.split(' ')[0];
    if (first.includes('-')) return first;
    return ts;
  };

  const renderDay = ({ item: dayDate }) => {
    const dayPunches = punches.filter(p => normalizeDate(p.timestamp) === dayDate).sort((a,b) => a.id - b.id);
    let totalStr = '--';

    if (dayPunches.length > 0) {
      const clockIns = dayPunches.filter(p => p.punch_type === 'CLOCK_IN').sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
      const clockOuts = dayPunches.filter(p => p.punch_type === 'CLOCK_OUT').sort((a,b) => new Date(b.timestamp) - new Date(a.timestamp));

      if (clockIns.length > 0 && clockOuts.length > 0) {
        const firstIn = new Date(clockIns[0].timestamp);
        const lastOut = new Date(clockOuts[0].timestamp);
        if (firstIn && lastOut && !isNaN(firstIn) && !isNaN(lastOut) && lastOut >= firstIn) {
          const diffMs = lastOut - firstIn;
          const diffHrs = Math.floor(diffMs / 3600000);
          const diffMins = Math.floor((diffMs % 3600000) / 60000);
          totalStr = `${diffHrs}:${diffMins.toString().padStart(2, '0')} hrs`;
        }
      } else if (clockIns.length > 0) {
        totalStr = 'Active shift';
      }
    }

    const dObj = new Date(dayDate);
    const dateNum = String(dObj.getDate()).padStart(2, '0');
    const dayName = dObj.toLocaleDateString('en-US', { weekday: 'short' });
    const isFuture = dObj > new Date();

    return (
      <View style={[styles.punchCard, { opacity: isFuture ? 0.6 : 1 }]}>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View style={{ flexDirection: 'column', alignItems: 'center', width: 45, borderRightWidth: 1, borderRightColor: '#f1f5f9', paddingRight: 10 }}>
            <Text style={{ fontSize: 20, fontWeight: '700', color: '#0f172a' }}>{dateNum}</Text>
            <Text style={{ fontSize: 13, fontWeight: '500', color: '#64748b' }}>{dayName}</Text>
          </View>
          <View style={{ flex: 1, paddingLeft: 12 }}>
            <Text style={{ fontSize: 14, color: '#64748b', fontWeight: '500' }}>
              Daily Total: <Text style={{ color: totalStr === '--' ? '#94a3b8' : '#0284c7', fontWeight: '700' }}>{totalStr}</Text>
            </Text>
          </View>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerBox}>
         <Ionicons name="calendar" size={24} color="#0284c7" />
         <View style={{ marginLeft: 10 }}>
           <Text style={styles.headerTitle}>Current Cutoff Period</Text>
           <Text style={styles.headerSubtitle}>{periodLabel}</Text>
         </View>
      </View>
      {loading ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#0284c7" />
        </View>
      ) : (
        <FlatList 
          data={cutoffDays} 
          keyExtractor={(item) => item}
          contentContainerStyle={{ paddingBottom: 20 }}
          showsVerticalScrollIndicator={false}
          renderItem={renderDay}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f8fafc' },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  headerBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ffffff', padding: 16, borderRadius: 12, marginBottom: 16, borderWidth: 1, borderColor: '#e2e8f0' },
  headerTitle: { fontSize: 15, fontWeight: '700', color: '#0f172a' },
  headerSubtitle: { fontSize: 13, color: '#64748b', marginTop: 2 },
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
  }
});
