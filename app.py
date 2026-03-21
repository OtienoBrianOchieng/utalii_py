# app.py
import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from flask_mail import Mail
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()

def create_app():
    """Application factory"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///kenya_tourism.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # File upload
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    app.config['ALLOWED_EXTENSIONS'] = set(os.environ.get('ALLOWED_EXTENSIONS', 'png,jpg,jpeg,gif').split(','))
    
    # Email
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@kenyatourism.com')
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    
    # CORS - Allow frontend origins
    allowed_origins = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')
    CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    # Register blueprints
    register_blueprints(app)
    
    # Create tables and default admin
    with app.app_context():
        db.create_all()
        create_default_admin()
        seed_sample_data()
    
    # Health check route
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'message': 'Kenya Tourism API is running'}), 200
    
    return app

def register_blueprints(app):
    """Register all route blueprints"""
    from routes.auth_routes import auth_bp
    from routes.destination_routes import destination_bp
    from routes.hotel_routes import hotel_bp
    from routes.booking_routes import booking_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(destination_bp, url_prefix='/api/destinations')
    app.register_blueprint(hotel_bp, url_prefix='/api/hotels')
    app.register_blueprint(booking_bp, url_prefix='/api/bookings')

def create_default_admin():
    """Create default admin user if none exists"""
    from models.user import User
    from werkzeug.security import generate_password_hash
    
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@kenyatourism.com')
    admin = User.query.filter_by(email=admin_email).first()
    
    if not admin:
        admin = User(
            full_name='System Administrator',
            email=admin_email,
            password_hash=generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'Admin@123456')),
            user_type='admin',
            is_verified=True,
            agreed_to_policy=True
        )
        db.session.add(admin)
        db.session.commit()
        print(f"✅ Default admin created: {admin_email}")

def seed_sample_data():
    """Seed sample destinations and hotels if database is empty"""
    from models.destination import Destination, DestinationImage, DestinationVideo
    from models.hotel import Hotel, Amenity, HotelImage, RestaurantMenu, MenuCategory, MenuItem
    from models.booking import Booking
    
    # Check if data already exists
    if Destination.query.count() > 0:
        return
    
    print("🌱 Seeding sample data...")
    
    # Create amenities
    amenities_data = [
        {'name': 'Free WiFi', 'icon': 'wifi'},
        {'name': 'Swimming Pool', 'icon': 'swimmer'},
        {'name': 'Restaurant', 'icon': 'utensils'},
        {'name': 'Bar', 'icon': 'cocktail'},
        {'name': 'Spa', 'icon': 'spa'},
        {'name': 'Gym', 'icon': 'dumbbell'},
        {'name': 'Free Parking', 'icon': 'parking'},
        {'name': 'Airport Shuttle', 'icon': 'shuttle-van'},
        {'name': 'Room Service', 'icon': 'concierge-bell'},
        {'name': 'Beach Access', 'icon': 'umbrella-beach'},
        {'name': 'Kids Club', 'icon': 'child'},
        {'name': 'Business Center', 'icon': 'briefcase'}
    ]
    
    amenities = {}
    for a in amenities_data:
        amenity = Amenity(**a)
        db.session.add(amenity)
        amenities[a['name']] = amenity
    
    # Create destinations
    destinations_data = [
        {
            'name': 'Maasai Mara National Reserve',
            'description': 'One of Africa\'s most famous safari destinations, known for the Great Migration and abundant wildlife including the Big Five. The reserve offers spectacular game viewing year-round with the best experience during the migration season from July to October.',
            'latitude': -1.4942,
            'longitude': 35.1444,
            'category': 'National Park',
            'region': 'Rift Valley',
            'best_time_to_visit': 'July to October (Great Migration)',
            'entry_fee': '$70 per day for adults',
            'opening_hours': '6:00 AM - 6:00 PM daily',
            'website': 'https://www.masaimara.travel'
        },
        {
            'name': 'Diani Beach',
            'description': 'Stunning white sand beach on the Indian Ocean, perfect for swimming, snorkeling, and water sports. The beach is lined with palm trees and offers excellent resorts, restaurants, and water activities.',
            'latitude': -4.2845,
            'longitude': 39.5833,
            'category': 'Beach',
            'region': 'Coast',
            'best_time_to_visit': 'December to March, July to October',
            'entry_fee': 'Free public access',
            'opening_hours': '24 hours',
            'website': 'https://www.dianibeach.com'
        },
        {
            'name': 'Amboseli National Park',
            'description': 'Famous for large elephant herds and spectacular views of Mount Kilimanjaro. The park offers classic African scenery with swamps, savanna, and the highest peak in Africa as a backdrop.',
            'latitude': -2.6389,
            'longitude': 37.2633,
            'category': 'National Park',
            'region': 'Rift Valley',
            'best_time_to_visit': 'June to October, January to February',
            'entry_fee': '$60 per day for adults',
            'opening_hours': '6:00 AM - 6:00 PM daily',
            'website': 'https://www.amboseli.com'
        },
        {
            'name': 'Lamu Old Town',
            'description': 'UNESCO World Heritage site, East Africa\'s oldest living Swahili settlement with rich history, unique architecture, and no motorized vehicles. Experience traditional dhow sailing and Swahili culture.',
            'latitude': -2.2694,
            'longitude': 40.9019,
            'category': 'Cultural',
            'region': 'Coast',
            'best_time_to_visit': 'July to March',
            'entry_fee': 'Free to explore',
            'opening_hours': '24 hours',
            'website': 'https://www.lamu.org'
        },
        {
            'name': 'Mount Kenya',
            'description': 'Africa\'s second-highest mountain, offering challenging climbs and beautiful hiking trails through diverse ecosystems from rainforest to alpine zones.',
            'latitude': -0.1521,
            'longitude': 37.3084,
            'category': 'Mountain',
            'region': 'Central Highlands',
            'best_time_to_visit': 'January to February, August to September',
            'entry_fee': '$52 per day for climbers',
            'opening_hours': '24 hours for climbing, park gates 6 AM-6 PM',
            'website': 'https://www.mountkenya.org'
        }
    ]
    
    destinations = {}
    for dest_data in destinations_data:
        dest = Destination(**dest_data)
        db.session.add(dest)
        destinations[dest_data['name']] = dest
    
    db.session.commit()
    
    # Create hotels for Maasai Mara
    maasai_mara = destinations['Maasai Mara National Reserve']
    mara_hotels = [
        {
            'name': 'Mara Serena Safari Lodge',
            'description': 'Perched on a hilltop overlooking the Mara River, this lodge offers stunning views and luxurious accommodations in the heart of the reserve. Each room features floor-to-ceiling windows overlooking the savanna.',
            'address': 'Maasai Mara National Reserve',
            'latitude': -1.4942,
            'longitude': 35.1444,
            'phone': '+254 20 2843000',
            'email': 'reservations@serenahotels.com',
            'website': 'https://www.serenahotels.com',
            'price_range': 'Luxury',
            'check_in_time': '12:00 PM',
            'check_out_time': '10:00 AM',
            'rating': 4.7
        },
        {
            'name': 'Angama Mara',
            'description': 'Perched on the edge of the Great Rift Valley, Angama Mara offers unparalleled views of the Mara Triangle with world-class service and accommodations. Inspired by the film "Out of Africa".',
            'address': 'Maasai Mara National Reserve',
            'latitude': -1.4930,
            'longitude': 35.1450,
            'phone': '+254 20 514 7300',
            'email': 'reservations@angama.com',
            'website': 'https://www.angama.com',
            'price_range': 'Luxury',
            'check_in_time': '2:00 PM',
            'check_out_time': '11:00 AM',
            'rating': 4.9
        }
    ]
    
    mara_hotel_objects = []
    for hotel_data in mara_hotels:
        hotel = Hotel(destination_id=maasai_mara.id, **hotel_data)
        db.session.add(hotel)
        mara_hotel_objects.append(hotel)
    
    # Create hotels for Diani Beach
    diani = destinations['Diani Beach']
    diani_hotels = [
        {
            'name': 'The Sands at Nomad',
            'description': 'Boutique hotel on Diani Beach featuring Swahili-style architecture, oceanfront rooms, and a renowned restaurant. Perfect for honeymooners and beach lovers.',
            'address': 'Diani Beach Road, Diani Beach',
            'latitude': -4.2845,
            'longitude': 39.5833,
            'phone': '+254 40 320 3223',
            'email': 'info@thesandsatnomad.com',
            'website': 'https://www.thesandsatnomad.com',
            'price_range': 'Mid-range',
            'check_in_time': '2:00 PM',
            'check_out_time': '11:00 AM',
            'rating': 4.6
        },
        {
            'name': 'Alfajiri Villas',
            'description': 'Luxury private villas with personal butler service, infinity pools, and direct beach access. Each villa comes with a dedicated staff including a chef.',
            'address': 'Diani Beach Road, Diani Beach',
            'latitude': -4.2850,
            'longitude': 39.5840,
            'phone': '+254 722 203838',
            'email': 'reservations@alfajiri.com',
            'website': 'https://www.alfajiri.com',
            'price_range': 'Luxury',
            'check_in_time': '2:00 PM',
            'check_out_time': '11:00 AM',
            'rating': 4.8
        }
    ]
    
    diani_hotel_objects = []
    for hotel_data in diani_hotels:
        hotel = Hotel(destination_id=diani.id, **hotel_data)
        db.session.add(hotel)
        diani_hotel_objects.append(hotel)
    
    db.session.commit()
    
    # Add amenities to hotels
    for hotel in mara_hotel_objects:
        if hotel.name == 'Mara Serena Safari Lodge':
            hotel.amenities.extend([
                amenities['Free WiFi'], amenities['Swimming Pool'], 
                amenities['Restaurant'], amenities['Bar'], amenities['Spa']
            ])
        elif hotel.name == 'Angama Mara':
            hotel.amenities.extend([
                amenities['Free WiFi'], amenities['Swimming Pool'], 
                amenities['Restaurant'], amenities['Bar'], amenities['Spa'],
                amenities['Gym'], amenities['Room Service']
            ])
    
    for hotel in diani_hotel_objects:
        if hotel.name == 'The Sands at Nomad':
            hotel.amenities.extend([
                amenities['Free WiFi'], amenities['Swimming Pool'],
                amenities['Restaurant'], amenities['Bar'], amenities['Beach Access']
            ])
        elif hotel.name == 'Alfajiri Villas':
            hotel.amenities.extend([
                amenities['Free WiFi'], amenities['Swimming Pool'],
                amenities['Restaurant'], amenities['Bar'], amenities['Spa'],
                amenities['Beach Access'], amenities['Room Service']
            ])
    
    db.session.commit()
    
    # Create restaurant menus
    for hotel in mara_hotel_objects + diani_hotel_objects:
        menu = RestaurantMenu(
            hotel_id=hotel.id,
            restaurant_name=f"{hotel.name} Restaurant",
            cuisine_type='Kenyan & International',
            description='Experience the finest dining with a blend of local Kenyan specialties and international cuisine.',
            opening_hours='Breakfast: 6:30-9:30, Lunch: 12:30-14:30, Dinner: 19:00-21:30',
            dress_code='Smart Casual',
            reservation_required=False
        )
        db.session.add(menu)
        db.session.commit()
        
        # Menu Categories
        breakfast = MenuCategory(
            restaurant_id=menu.id,
            name='Breakfast',
            description='Start your day with a hearty breakfast',
            order_index=1
        )
        lunch = MenuCategory(
            restaurant_id=menu.id,
            name='Lunch',
            description='Light meals and snacks',
            order_index=2
        )
        dinner = MenuCategory(
            restaurant_id=menu.id,
            name='Dinner',
            description='Evening dining with Kenyan specialties',
            order_index=3
        )
        db.session.add_all([breakfast, lunch, dinner])
        db.session.commit()
        
        # Breakfast items
        breakfast_items = [
            {
                'name': 'Full English Breakfast',
                'description': 'Eggs, bacon, sausage, grilled tomatoes, mushrooms, and baked beans',
                'price': 25,
                'currency': 'USD',
                'dietary_info': 'Contains meat',
                'spicy_level': 0
            },
            {
                'name': 'Kenyan Breakfast',
                'description': 'Ugali, sukuma wiki, eggs, and grilled meat',
                'price': 22,
                'currency': 'USD',
                'dietary_info': 'Contains meat,Gluten-free option available',
                'spicy_level': 1
            },
            {
                'name': 'Continental Breakfast',
                'description': 'Pastries, fresh fruits, yogurt, cereal, and juice',
                'price': 18,
                'currency': 'USD',
                'dietary_info': 'Vegetarian',
                'spicy_level': 0
            }
        ]
        
        for item_data in breakfast_items:
            item = MenuItem(category_id=breakfast.id, **item_data)
            db.session.add(item)
        
        # Lunch items
        lunch_items = [
            {
                'name': 'Grilled Fish',
                'description': 'Fresh tilapia grilled with herbs, served with ugali and kachumbari',
                'price': 28,
                'currency': 'USD',
                'dietary_info': 'Gluten-free',
                'spicy_level': 1,
                'is_special': True
            },
            {
                'name': 'Chicken Curry',
                'description': 'Tender chicken in aromatic curry sauce, served with rice',
                'price': 26,
                'currency': 'USD',
                'dietary_info': 'Contains dairy',
                'spicy_level': 2
            }
        ]
        
        for item_data in lunch_items:
            item = MenuItem(category_id=lunch.id, **item_data)
            db.session.add(item)
        
        # Dinner items
        dinner_items = [
            {
                'name': 'Nyama Choma',
                'description': 'Traditional Kenyan roasted meat (goat or beef) served with ugali and kachumbari',
                'price': 35,
                'currency': 'USD',
                'dietary_info': 'Contains meat,Gluten-free',
                'spicy_level': 1,
                'is_special': True
            },
            {
                'name': 'Vegetable Pilau',
                'description': 'Fragrant rice cooked with spices and mixed vegetables',
                'price': 22,
                'currency': 'USD',
                'dietary_info': 'Vegetarian,Vegan',
                'spicy_level': 1
            }
        ]
        
        for item_data in dinner_items:
            item = MenuItem(category_id=dinner.id, **item_data)
            db.session.add(item)
        
        db.session.commit()
    
    print("✅ Sample data seeded successfully")

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)