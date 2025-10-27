import json
import requests
from tqdm import tqdm
import os
from datetime import datetime
import signal
import sys
import time


class DogImagesDownloader:
    """Main class for downloading dog images and uploading to Yandex.Disk"""

    def __init__(self):
        self.session = requests.Session()
        self.results = []
        self.is_interrupted = False
        self.setup_interrupt_handler()
        self.setup_yandex_token()

    def setup_interrupt_handler(self):
        """Setup handler for Ctrl+C interruption"""

        def signal_handler(sig, frame):
            print("\n\n⚠️ Получен сигнал прерывания (Ctrl+C)...")
            self.is_interrupted = True
            self.save_results()
            print("💾 Текущий прогресс сохранен в dog_images_backup.json")
            print("👋 Завершение работы...")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

    def setup_yandex_token(self):
        """Request Yandex Disk token from user"""
        print("=" * 50)
        print("Yandex.Disk Token Setup")
        print("=" * 50)

        self.token = input("Please enter your Yandex.Disk token: ").strip()

        if not self.token:
            raise ValueError("Token cannot be empty!")

        self.session.headers.update({
            'Authorization': f'OAuth {self.token}'
        })

        # Test the token
        if not self.test_yandex_token():
            raise ValueError("Invalid token! Please check your token and try again.")

    def test_yandex_token(self):
        """Test if the Yandex Disk token is valid"""
        try:
            response = self.session.get("https://cloud-api.yandex.net/v1/disk/resources",
                                        params={'path': '/'})
            return response.status_code == 200
        except:
            return False

    def get_all_breeds(self):
        """Get list of all dog breeds from dog.ceo API"""
        print("Fetching list of all dog breeds...")
        response = self.session.get("https://dog.ceo/api/breeds/list/all")
        response.raise_for_status()
        data = response.json()

        if data['status'] != 'success':
            raise Exception("Failed to fetch breeds list")

        return data['message']

    def get_breed_images(self, breed, sub_breed=None, count=1):
        """Get images for a breed or sub-breed"""
        if sub_breed:
            url = f"https://dog.ceo/api/breed/{breed}/{sub_breed}/images/random/{count}"
        else:
            url = f"https://dog.ceo/api/breed/{breed}/images/random/{count}"

        response = self.session.get(url)
        response.raise_for_status()
        data = response.json()

        if data['status'] != 'success':
            return []

        return data['message']

    def create_yandex_folder(self, folder_path):
        """Create folder on Yandex.Disk"""
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {'path': folder_path}

        response = self.session.put(url, params=params)

        # Folder already exists is not an error
        if response.status_code not in [201, 409]:
            response.raise_for_status()
        return True

    def upload_to_yandex_disk(self, file_url, remote_path):
        """Upload file to Yandex.Disk by URL"""
        url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
        params = {
            'path': remote_path,
            'url': file_url
        }

        response = self.session.post(url, params=params)

        if response.status_code == 202:
            return True
        elif response.status_code == 409:
            print(f"File already exists: {remote_path}")
            return True
        else:
            response.raise_for_status()
            return False

    def get_file_size_from_url(self, url):
        """Get file size from URL without downloading the whole file"""
        try:
            response = self.session.head(url)
            return int(response.headers.get('content-length', 0))
        except:
            return 0

    def process_breed(self, breed, sub_breeds):
        """Process a single breed and its sub-breeds"""
        if self.is_interrupted:
            return 0

        breed_folder = f"DogBreeds/{breed}"

        # Create breed folder on Yandex.Disk
        self.create_yandex_folder(breed_folder)

        processed_count = 0

        if sub_breeds:
            # Process each sub-breed
            for sub_breed in sub_breeds:
                if self.is_interrupted:
                    break
                if self._process_sub_breed(breed, sub_breed, breed_folder):
                    processed_count += 1
        else:
            # Process main breed
            if self._process_main_breed(breed, breed_folder):
                processed_count += 1

        # ✅ СОХРАНЯЕМ ПОСЛЕ КАЖДОЙ ПОРОДЫ
        self.save_results()
        print(f"💾 Прогресс сохранен после породы: {breed}")

        return processed_count

    def _process_sub_breed(self, breed, sub_breed, breed_folder):
        """Process a single sub-breed"""
        try:
            image_urls = self.get_breed_images(breed, sub_breed, 1)
            if not image_urls:
                print(f"  No image found for {breed}/{sub_breed}")
                return False

            image_url = image_urls[0]
            return self._upload_image(breed, sub_breed, image_url, breed_folder)
        except Exception as e:
            print(f"  Error processing {breed}/{sub_breed}: {e}")
            return False

    def _process_main_breed(self, breed, breed_folder):
        """Process main breed without sub-breeds"""
        try:
            image_urls = self.get_breed_images(breed, count=1)
            if not image_urls:
                print(f"  No image found for {breed}")
                return False

            image_url = image_urls[0]
            return self._upload_image(breed, None, image_url, breed_folder)
        except Exception as e:
            print(f"  Error processing {breed}: {e}")
            return False

    def _upload_image(self, breed, sub_breed, image_url, breed_folder):
        """Upload single image and record information"""
        # Extract filename from URL
        filename = image_url.split('/')[-1]

        if sub_breed:
            remote_filename = f"{breed}_{sub_breed}_{filename}"
        else:
            remote_filename = f"{breed}_{filename}"

        remote_path = f"{breed_folder}/{remote_filename}"

        # Get file size before upload
        file_size = self.get_file_size_from_url(image_url)

        # Upload to Yandex.Disk
        if self.upload_to_yandex_disk(image_url, remote_path):
            # Record detailed information
            file_info = {
                'breed': breed,
                'sub_breed': sub_breed,
                'file_name': remote_filename,
                'remote_path': remote_path,
                'source_url': image_url,
                'file_size': {
                    'bytes': file_size,
                    'kilobytes': round(file_size / 1024, 2),
                    'megabytes': round(file_size / (1024 * 1024), 3)
                },
                'upload_info': {
                    'timestamp': datetime.now().isoformat(),
                    'status': 'success'
                },
                'yandex_disk_info': {
                    'folder': breed_folder,
                    'full_path': remote_path
                }
            }

            self.results.append(file_info)
            return True
        return False

    def save_results(self):
        """Save detailed results to JSON file"""
        try:
            results_data = {
                'metadata': {
                    'total_images': len(self.results),
                    'total_breeds_processed': len(set(r['breed'] for r in self.results)),
                    'generated_at': datetime.now().isoformat(),
                    'api_used': 'dog.ceo',
                    'interrupted': self.is_interrupted
                },
                'files': self.results
            }

            with open("dog_images_backup.json", 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False, sort_keys=True)

            # ✅ ВСЕГДА показываем где файл
            current_dir = os.getcwd()
            file_path = os.path.join(current_dir, "dog_images_backup.json")
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            print(f"📁 Файл сохранен: {file_path} ({file_size} байт)")

        except Exception as e:
            print(f"❌ Ошибка при сохранении JSON: {e}")

    def print_statistics(self):
        """Print download statistics"""
        total_size = sum(r['file_size']['bytes'] for r in self.results)
        breeds_count = len(set(r['breed'] for r in self.results))

        print(f"\n" + "=" * 50)
        print("DOWNLOAD STATISTICS")
        print("=" * 50)
        print(f"Total breeds processed: {breeds_count}")
        print(f"Total images uploaded: {len(self.results)}")
        print(f"Total size: {total_size} bytes ({total_size / 1024 / 1024:.2f} MB)")
        print(f"Interrupted: {'Yes' if self.is_interrupted else 'No'}")
        print(f"Results saved to: dog_images_backup.json")
        print("=" * 50)

    def run(self):
        """Main method to run the downloader"""
        print("Starting Dog Images Downloader")
        print("=" * 50)
        print("💡 Совет: Нажмите Ctrl+C в любой момент для сохранения прогресса")
        print("=" * 50)

        try:
            # Create base folder on Yandex.Disk
            print("Creating base folder on Yandex.Disk...")
            self.create_yandex_folder("DogBreeds")

            # Get all breeds
            all_breeds = self.get_all_breeds()
            print(f"Found {len(all_breeds)} breeds")

            total_processed = 0

            # Process each breed with progress bar
            for breed, sub_breeds in tqdm(all_breeds.items(), desc="Processing breeds"):
                if self.is_interrupted:
                    break

                print(f"\nProcessing breed: {breed}")
                if sub_breeds:
                    print(f"  Sub-breeds: {', '.join(sub_breeds)}")

                processed = self.process_breed(breed, sub_breeds)
                total_processed += processed
                print(f"  Uploaded {processed} images for {breed}")

            # Final save
            self.save_results()
            self.print_statistics()

        except requests.exceptions.RequestException as e:
            print(f"Network error occurred: {e}")
            self.save_results()
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.save_results()
            raise


if __name__ == "__main__":
    try:
        downloader = DogImagesDownloader()
        downloader.run()
    except KeyboardInterrupt:
        print("\n👋 Программа завершена пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
    finally:
        print("\n🎯 Работа программы завершена")