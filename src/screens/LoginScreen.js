import React, { useState, useEffect, useContext } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function LoginScreen() {
  const { login, register, API_BASE_URL } = useContext(AuthContext);
  const [isRegisterMode, setIsRegisterMode] = useState(false);

  // Login States
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  // Signup States
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [suffix, setSuffix] = useState('');
  const [email, setEmail] = useState('');
  const [mobilePhone, setMobilePhone] = useState('');

  // Department Dropdown States
  const [department, setDepartment] = useState('IT Operations');
  const [departmentsList, setDepartmentsList] = useState(['Admin', 'IT Operations', 'Executive', 'Operations', 'Sales', 'HR']);
  const [showDeptDropdown, setShowDeptDropdown] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadSavedCredentials();
    fetchDynamicDepartments();
  }, []);

  const fetchDynamicDepartments = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/jobs`);
      if (response.ok) {
        const data = await response.json();
        if (Array.isArray(data) && data.length > 0) {
          const catNames = data.map(cat => cat.name);
          setDepartmentsList(Array.from(new Set([...catNames, 'Admin', 'HR', 'IT Operations'])));
        }
      }
    } catch (e) {
      console.log('Using default department list fallback:', e);
    }
  };

  const loadSavedCredentials = async () => {
    try {
      const savedEmpId = await AsyncStorage.getItem('hris_last_emp_id');
      const savedDept = await AsyncStorage.getItem('hris_last_dept');
      const savedPwd = await AsyncStorage.getItem('hris_last_password');
      const savedRemember = await AsyncStorage.getItem('hris_remember_me');

      if (savedEmpId) setEmployeeId(savedEmpId);
      if (savedDept) setDepartment(savedDept);
      if (savedRemember === 'true') {
        setRememberMe(true);
        if (savedPwd) setPassword(savedPwd);
      } else if (savedRemember === 'false') {
        setRememberMe(false);
      }
    } catch (e) {
      console.log('Error reading storage:', e);
    }
  };

  const handleLogin = async () => {
    if (!employeeId || !password) {
      Alert.alert('Missing Fields', 'Please enter your Employee ID / Email and Password.');
      return;
    }

    setLoading(true);
    try {
      if (rememberMe) {
        await AsyncStorage.setItem('hris_last_emp_id', employeeId);
        await AsyncStorage.setItem('hris_last_dept', department);
        await AsyncStorage.setItem('hris_last_password', password);
        await AsyncStorage.setItem('hris_remember_me', 'true');
      } else {
        await AsyncStorage.removeItem('hris_last_password');
        await AsyncStorage.setItem('hris_remember_me', 'false');
      }

      const res = await login(employeeId, password, department);
      if (!res.success) {
        const errMsg = typeof res.message === 'object' ? JSON.stringify(res.message) : (res.message || 'Invalid Credentials');
        Alert.alert('Authentication Failed', errMsg);
      }
    } catch (error) {
      Alert.alert('Login Error', error.message || 'Unable to connect to HRIS backend server.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!firstName || !lastName || !email || !password || !department || !mobilePhone) {
      Alert.alert('Missing Fields', 'Please fill in First Name, Last Name, Email, Password, Department, and Mobile Phone.');
      return;
    }

    setLoading(true);
    try {
      const res = await register(firstName, lastName, suffix, email, password, department, mobilePhone);

      if (res.success) {
        const fullDispName = `${firstName} ${lastName} ${suffix}`.trim();
        Alert.alert(
          'Join Request Submitted',
          `Join request sent for ${fullDispName}! Pending admin approval. Generated ID: ${res.employeeId}`,
          [{ text: 'OK', onPress: () => setIsRegisterMode(false) }]
        );
      } else {
        const errMsg = typeof res.message === 'object' ? JSON.stringify(res.message) : (res.message || 'Failed to submit join request.');
        Alert.alert('Registration Failed', errMsg);
      }
    } catch (e) {
      Alert.alert('Error', 'Unable to connect to backend server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        <View style={styles.card}>
          <View style={styles.logoBadge}>
            <Ionicons name="shield-checkmark" size={32} color="#ffffff" />
          </View>

          <Text style={styles.title}>HRIS Portal</Text>
          <Text style={styles.subtitle}>
            {isRegisterMode ? 'Request to join your organization' : 'Sign in to access your attendance workspace'}
          </Text>

          {isRegisterMode ? (
            /* REGISTRATION FORM */
            <>
              <View style={styles.inputGroup}>
                <Text style={styles.label}>First Name</Text>
                <View style={styles.inputWrapper}>
                  <Ionicons name="person-outline" size={18} color="#64748b" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="e.g. Juan"
                    value={firstName}
                    onChangeText={setFirstName}
                  />
                </View>
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Last Name</Text>
                <View style={styles.inputWrapper}>
                  <Ionicons name="person-outline" size={18} color="#64748b" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="e.g. Santos"
                    value={lastName}
                    onChangeText={setLastName}
                  />
                </View>
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Suffix (Optional)</Text>
                <View style={styles.inputWrapper}>
                  <Ionicons name="information-circle-outline" size={18} color="#64748b" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="e.g. Jr., III"
                    value={suffix}
                    onChangeText={setSuffix}
                  />
                </View>
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Email Address</Text>
                <View style={styles.inputWrapper}>
                  <Ionicons name="mail-outline" size={18} color="#64748b" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="e.g. juan@organization.com"
                    value={email}
                    onChangeText={setEmail}
                    keyboardType="email-address"
                    autoCapitalize="none"
                  />
                </View>
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Mobile Phone Number</Text>
                <View style={styles.inputWrapper}>
                  <Ionicons name="call-outline" size={18} color="#64748b" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="e.g. 09989400957"
                    value={mobilePhone}
                    onChangeText={setMobilePhone}
                    keyboardType="phone-pad"
                  />
                </View>
              </View>
            </>
          ) : (
            /* LOGIN EMPLOYEE ID FIELD */
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Employee ID or Email</Text>
              <View style={styles.inputWrapper}>
                <Ionicons name="person-outline" size={18} color="#64748b" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="e.g. 3286 or email"
                  value={employeeId}
                  onChangeText={setEmployeeId}
                  autoCapitalize="none"
                />
              </View>
            </View>
          )}

          {/* DEPARTMENT DROPDOWN */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Department Assignment</Text>
            <TouchableOpacity
              style={styles.dropdownTrigger}
              activeOpacity={0.8}
              onPress={() => setShowDeptDropdown(!showDeptDropdown)}
            >
              <Ionicons name="business-outline" size={18} color="#64748b" style={styles.inputIcon} />
              <Text style={styles.dropdownValueText}>{department}</Text>
              <Ionicons name={showDeptDropdown ? "chevron-up" : "chevron-down"} size={18} color="#64748b" />
            </TouchableOpacity>

            {showDeptDropdown && (
              <View style={styles.dropdownMenu}>
                {departmentsList.map((dept) => (
                  <TouchableOpacity
                    key={dept}
                    style={[styles.dropdownItem, department === dept && styles.dropdownItemActive]}
                    onPress={() => {
                      setDepartment(dept);
                      setShowDeptDropdown(false);
                    }}
                  >
                    <Text style={[styles.dropdownItemText, department === dept && styles.dropdownItemTextActive]}>
                      {dept}
                    </Text>
                    {department === dept && <Ionicons name="checkmark" size={16} color="#2563eb" />}
                  </TouchableOpacity>
                ))}
              </View>
            )}
          </View>

          {/* PASSWORD FIELD */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Password</Text>
            <View style={styles.inputWrapper}>
              <Ionicons name="lock-closed-outline" size={18} color="#64748b" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="••••••••"
                secureTextEntry={!showPassword}
                value={password}
                onChangeText={setPassword}
              />
              <TouchableOpacity onPress={() => setShowPassword(!showPassword)} style={styles.eyeBtn}>
                <Ionicons name={showPassword ? "eye-off-outline" : "eye-outline"} size={20} color="#64748b" />
              </TouchableOpacity>
            </View>
          </View>

          {/* REMEMBER PASSWORD CHECKBOX (LOGIN MODE ONLY) */}
          {!isRegisterMode && (
            <TouchableOpacity
              style={styles.rememberRow}
              activeOpacity={0.8}
              onPress={() => setRememberMe(!rememberMe)}
            >
              <Ionicons
                name={rememberMe ? "checkbox" : "square-outline"}
                size={20}
                color={rememberMe ? "#2563eb" : "#64748b"}
              />
              <Text style={styles.rememberText}>Remember password on this device</Text>
            </TouchableOpacity>
          )}

          {/* SUBMIT BUTTON */}
          <TouchableOpacity
            style={styles.submitBtn}
            onPress={isRegisterMode ? handleRegister : handleLogin}
            disabled={loading}
            activeOpacity={0.85}
          >
            {loading ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={styles.submitBtnText}>
                {isRegisterMode ? 'Submit Join Request' : 'Sign In'}
              </Text>
            )}
          </TouchableOpacity>

          {/* MODE TOGGLE */}
          <TouchableOpacity
            style={styles.toggleBtn}
            onPress={() => setIsRegisterMode(!isRegisterMode)}
          >
            <Text style={styles.toggleBtnText}>
              {isRegisterMode
                ? 'Already have an account? Sign In'
                : 'Need to join an organization? Request Sign Up'}
            </Text>
          </TouchableOpacity>

        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  scrollContent: { flexGrow: 1, justifyContent: 'center', padding: 20 },
  card: { backgroundColor: '#ffffff', borderRadius: 20, padding: 24, borderWidth: 1, borderColor: '#f1f5f9', elevation: 3 },
  logoBadge: { width: 56, height: 56, borderRadius: 16, backgroundColor: '#2563eb', justifyContent: 'center', alignItems: 'center', alignSelf: 'center', marginBottom: 12 },
  title: { fontSize: 22, fontWeight: '800', color: '#0f172a', textAlign: 'center' },
  subtitle: { fontSize: 13, color: '#64748b', textAlign: 'center', marginBottom: 24 },
  inputGroup: { marginBottom: 16 },
  label: { fontSize: 12, fontWeight: '700', color: '#475569', marginBottom: 6 },
  inputWrapper: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 10, paddingHorizontal: 12, height: 46, backgroundColor: '#ffffff' },
  inputIcon: { marginRight: 8 },
  eyeBtn: { padding: 4 },
  input: { flex: 1, fontSize: 14, color: '#0f172a' },
  dropdownTrigger: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 10, paddingHorizontal: 12, height: 46, backgroundColor: '#ffffff' },
  dropdownValueText: { flex: 1, fontSize: 14, color: '#0f172a' },
  dropdownMenu: { marginTop: 4, borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 10, backgroundColor: '#ffffff', elevation: 4, overflow: 'hidden' },
  dropdownItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12, paddingHorizontal: 14, borderBottomWidth: 1, borderBottomColor: '#f1f5f9' },
  dropdownItemActive: { backgroundColor: '#eff6ff' },
  dropdownItemText: { fontSize: 13, color: '#334155' },
  dropdownItemTextActive: { color: '#2563eb', fontWeight: '700' },
  rememberRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 16 },
  rememberText: { fontSize: 13, color: '#475569', fontWeight: '500' },
  submitBtn: { backgroundColor: '#2563eb', height: 48, borderRadius: 10, justifyContent: 'center', alignItems: 'center', marginTop: 8 },
  submitBtnText: { color: '#ffffff', fontWeight: '700', fontSize: 15 },
  toggleBtn: { marginTop: 16, paddingVertical: 8, alignItems: 'center' },
  toggleBtnText: { color: '#0284c7', fontWeight: '700', fontSize: 13 },
});
