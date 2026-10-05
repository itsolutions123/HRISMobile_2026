import React, { useState, useEffect, useContext } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, KeyboardAvoidingView, Platform, ScrollView, Image } from 'react-native';
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
  const [departmentsList, setDepartmentsList] = useState([]);
  const [showDeptDropdown, setShowDeptDropdown] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadSavedCredentials();
    fetchDynamicDepartments();
  }, []);

  const fetchDynamicDepartments = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/departments`);
      if (response.ok) {
        const data = await response.json();
        if (Array.isArray(data) && data.length > 0) {
          setDepartmentsList(data);
          setDepartment(data[0]); // Auto-select the first valid group
        }
      }
    } catch (e) {
      console.log('Failed to fetch departments:', e);
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
          
          <Image source={require('../../assets/logo_gray.png')} style={styles.logo} resizeMode="contain" />

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
          {isRegisterMode && (
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
                      {department === dept && <Ionicons name="checkmark" size={16} color="#3b82f6" />}
                    </TouchableOpacity>
                  ))}
                </View>
              )}
            </View>
          )}

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
                size={22}
                color={rememberMe ? "#3b82f6" : "#64748b"}
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
  container: { 
    flex: 1, 
    backgroundColor: '#e2e8f0' // Soft clay backdrop
  },
  scrollContent: { 
    flexGrow: 1, 
    justifyContent: 'center', 
    padding: 20 
  },
  card: { 
    backgroundColor: '#f8fafc', 
    borderRadius: 32, 
    padding: 24, 
    borderWidth: 2, 
    borderColor: '#ffffff', 
    shadowColor: '#94a3b8', 
    shadowOffset: { width: 8, height: 8 }, 
    shadowOpacity: 0.4, 
    shadowRadius: 16, 
    elevation: 10 
  },
  logo: { 
    width: 140, 
    height: 140, 
    alignSelf: 'center', 
    marginBottom: 16 
  },
  subtitle: { 
    fontSize: 14, 
    color: '#64748b', 
    textAlign: 'center', 
    marginBottom: 24,
    fontWeight: '500'
  },
  inputGroup: { 
    marginBottom: 18 
  },
  label: { 
    fontSize: 12, 
    fontWeight: '700', 
    color: '#475569', 
    marginBottom: 8,
    marginLeft: 4
  },
  inputWrapper: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    borderWidth: 2, 
    borderColor: '#ffffff', 
    borderRadius: 20, 
    paddingHorizontal: 16, 
    height: 54, 
    backgroundColor: '#f1f5f9',
    shadowColor: '#94a3b8',
    shadowOffset: { width: 4, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 6,
    elevation: 3
  },
  inputIcon: { 
    marginRight: 10 
  },
  eyeBtn: { 
    padding: 4 
  },
  input: { 
    flex: 1, 
    fontSize: 15, 
    color: '#0f172a',
    fontWeight: '500'
  },
  dropdownTrigger: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    borderWidth: 2, 
    borderColor: '#ffffff', 
    borderRadius: 20, 
    paddingHorizontal: 16, 
    height: 54, 
    backgroundColor: '#f1f5f9',
    shadowColor: '#94a3b8',
    shadowOffset: { width: 4, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 6,
    elevation: 3
  },
  dropdownValueText: { 
    flex: 1, 
    fontSize: 15, 
    color: '#0f172a',
    fontWeight: '500'
  },
  dropdownMenu: { 
    marginTop: 8, 
    borderWidth: 2, 
    borderColor: '#ffffff', 
    borderRadius: 20, 
    backgroundColor: '#f8fafc', 
    shadowColor: '#94a3b8',
    shadowOffset: { width: 4, height: 8 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 6, 
    overflow: 'hidden' 
  },
  dropdownItem: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    paddingVertical: 14, 
    paddingHorizontal: 16, 
    borderBottomWidth: 1, 
    borderBottomColor: '#f1f5f9' 
  },
  dropdownItemActive: { 
    backgroundColor: '#eff6ff' 
  },
  dropdownItemText: { 
    fontSize: 14, 
    color: '#334155',
    fontWeight: '500'
  },
  dropdownItemTextActive: { 
    color: '#3b82f6', 
    fontWeight: '700' 
  },
  rememberRow: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    gap: 10, 
    marginBottom: 20,
    marginLeft: 4
  },
  rememberText: { 
    fontSize: 14, 
    color: '#475569', 
    fontWeight: '600' 
  },
  submitBtn: { 
    backgroundColor: '#3b82f6', 
    height: 54, 
    borderRadius: 20, 
    borderTopWidth: 1,
    borderTopColor: '#93c5fd', // Clay inner highlight
    justifyContent: 'center', 
    alignItems: 'center', 
    marginTop: 8,
    shadowColor: '#2563eb',
    shadowOffset: { width: 4, height: 8 },
    shadowOpacity: 0.4,
    shadowRadius: 12,
    elevation: 8
  },
  submitBtnText: { 
    color: '#ffffff', 
    fontWeight: '800', 
    fontSize: 16 
  },
  toggleBtn: { 
    marginTop: 20, 
    paddingVertical: 10, 
    alignItems: 'center' 
  },
  toggleBtnText: { 
    color: '#0ea5e9', 
    fontWeight: '700', 
    fontSize: 14 
  },
});
