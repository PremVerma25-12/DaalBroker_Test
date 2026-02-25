-- MySQL dump 10.13  Distrib 8.0.45, for Linux (x86_64)
--
-- Host: localhost    Database: daalbrokerdb
-- ------------------------------------------------------
-- Server version	8.0.45-0ubuntu0.24.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=81 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',3,'add_permission'),(6,'Can change permission',3,'change_permission'),(7,'Can delete permission',3,'delete_permission'),(8,'Can view permission',3,'view_permission'),(9,'Can add group',2,'add_group'),(10,'Can change group',2,'change_group'),(11,'Can delete group',2,'delete_group'),(12,'Can view group',2,'view_group'),(13,'Can add content type',4,'add_contenttype'),(14,'Can change content type',4,'change_contenttype'),(15,'Can delete content type',4,'delete_contenttype'),(16,'Can view content type',4,'view_contenttype'),(17,'Can add session',5,'add_session'),(18,'Can change session',5,'change_session'),(19,'Can delete session',5,'delete_session'),(20,'Can view session',5,'view_session'),(21,'Can add DAAL User',7,'add_daaluser'),(22,'Can change DAAL User',7,'change_daaluser'),(23,'Can delete DAAL User',7,'delete_daaluser'),(24,'Can view DAAL User',7,'view_daaluser'),(25,'Can add Category Master',6,'add_categorymaster'),(26,'Can change Category Master',6,'change_categorymaster'),(27,'Can delete Category Master',6,'delete_categorymaster'),(28,'Can view Category Master',6,'view_categorymaster'),(29,'Can add Sub-Category Master',12,'add_subcategorymaster'),(30,'Can change Sub-Category Master',12,'change_subcategorymaster'),(31,'Can delete Sub-Category Master',12,'delete_subcategorymaster'),(32,'Can view Sub-Category Master',12,'view_subcategorymaster'),(33,'Can add Polish Master',8,'add_polishmaster'),(34,'Can change Polish Master',8,'change_polishmaster'),(35,'Can delete Polish Master',8,'delete_polishmaster'),(36,'Can view Polish Master',8,'view_polishmaster'),(37,'Can add Product',9,'add_product'),(38,'Can change Product',9,'change_product'),(39,'Can delete Product',9,'delete_product'),(40,'Can view Product',9,'view_product'),(41,'Can add Product Image',10,'add_productimage'),(42,'Can change Product Image',10,'change_productimage'),(43,'Can delete Product Image',10,'delete_productimage'),(44,'Can view Product Image',10,'view_productimage'),(45,'Can add Role Permission',11,'add_rolepermission'),(46,'Can change Role Permission',11,'change_rolepermission'),(47,'Can delete Role Permission',11,'delete_rolepermission'),(48,'Can view Role Permission',11,'view_rolepermission'),(49,'Can add Token',13,'add_token'),(50,'Can change Token',13,'change_token'),(51,'Can delete Token',13,'delete_token'),(52,'Can view Token',13,'view_token'),(53,'Can add Token',14,'add_tokenproxy'),(54,'Can change Token',14,'change_tokenproxy'),(55,'Can delete Token',14,'delete_tokenproxy'),(56,'Can view Token',14,'view_tokenproxy'),(57,'Can add Branch Master',15,'add_branchmaster'),(58,'Can change Branch Master',15,'change_branchmaster'),(59,'Can delete Branch Master',15,'delete_branchmaster'),(60,'Can view Branch Master',15,'view_branchmaster'),(61,'Can add product interest',16,'add_productinterest'),(62,'Can change product interest',16,'change_productinterest'),(63,'Can delete product interest',16,'delete_productinterest'),(64,'Can view product interest',16,'view_productinterest'),(65,'Can add Product Video',17,'add_productvideo'),(66,'Can change Product Video',17,'change_productvideo'),(67,'Can delete Product Video',17,'delete_productvideo'),(68,'Can view Product Video',17,'view_productvideo'),(69,'Can add Brand Master',18,'add_brandmaster'),(70,'Can change Brand Master',18,'change_brandmaster'),(71,'Can delete Brand Master',18,'delete_brandmaster'),(72,'Can view Brand Master',18,'view_brandmaster'),(73,'Can add Contract',19,'add_contract'),(74,'Can change Contract',19,'change_contract'),(75,'Can delete Contract',19,'delete_contract'),(76,'Can view Contract',19,'view_contract'),(77,'Can add Tag Master',20,'add_tagmaster'),(78,'Can change Tag Master',20,'change_tagmaster'),(79,'Can delete Tag Master',20,'delete_tagmaster'),(80,'Can view Tag Master',20,'view_tagmaster');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `authtoken_token`
--

DROP TABLE IF EXISTS `authtoken_token`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `authtoken_token` (
  `key` varchar(40) NOT NULL,
  `created` datetime(6) NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`key`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `authtoken_token_user_id_35299eff_fk_brokers_app_daaluser_id` FOREIGN KEY (`user_id`) REFERENCES `brokers_app_daaluser` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `authtoken_token`
--

LOCK TABLES `authtoken_token` WRITE;
/*!40000 ALTER TABLE `authtoken_token` DISABLE KEYS */;
INSERT INTO `authtoken_token` VALUES ('222415d5bd6f07dd25287a3ebd683aa932dced9f','2026-02-09 06:12:09.955279',2),('97e33aed152dfd046c7a0c3a6859c229f583ffcf','2026-02-07 09:38:08.402560',1);
/*!40000 ALTER TABLE `authtoken_token` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_branchmaster`
--

DROP TABLE IF EXISTS `brokers_app_branchmaster`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_branchmaster` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `location_name` varchar(150) NOT NULL,
  `state` varchar(120) NOT NULL,
  `city` varchar(120) NOT NULL,
  `area` varchar(150) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_branch_state_city_area` (`state`,`city`,`area`),
  KEY `brokers_app_state_8cfae4_idx` (`state`),
  KEY `brokers_app_city_21c444_idx` (`city`),
  KEY `brokers_app_area_606f70_idx` (`area`),
  KEY `brokers_app_branchmaster_is_active_334b4370` (`is_active`),
  KEY `brokers_app_branchmaster_created_at_22270aed` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_branchmaster`
--

LOCK TABLES `brokers_app_branchmaster` WRITE;
/*!40000 ALTER TABLE `brokers_app_branchmaster` DISABLE KEYS */;
INSERT INTO `brokers_app_branchmaster` VALUES (1,'Yong Farm','Assam','Bongaigaon','mp nagar',1,'2026-02-17 07:53:12.094226','2026-02-19 07:50:07.286278'),(2,'Bhopal Mill','Madhya Pradesh','Bhopal','Kamla Nagar',1,'2026-02-17 09:31:15.024791','2026-02-19 07:49:36.278847'),(3,'bhopal','Goa','Cavelossim','bhopal',1,'2026-02-19 12:56:05.972625','2026-02-20 11:14:26.138761'),(4,'Butibori','Maharashtra','Nagpur','Sitabardi',1,'2026-02-20 11:13:18.870096','2026-02-20 11:14:45.230653'),(5,'Butibori','Madhya Pradesh','Indore','bhopal',1,'2026-02-20 16:49:18.520946','2026-02-20 16:49:18.520976');
/*!40000 ALTER TABLE `brokers_app_branchmaster` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_brandmaster`
--

DROP TABLE IF EXISTS `brokers_app_brandmaster`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_brandmaster` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `brand_unique_id` varchar(20) NOT NULL,
  `brand_name` varchar(120) NOT NULL,
  `status` varchar(10) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `brand_unique_id` (`brand_unique_id`),
  UNIQUE KEY `brand_name` (`brand_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_brandmaster`
--

LOCK TABLES `brokers_app_brandmaster` WRITE;
/*!40000 ALTER TABLE `brokers_app_brandmaster` DISABLE KEYS */;
/*!40000 ALTER TABLE `brokers_app_brandmaster` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_categorymaster`
--

DROP TABLE IF EXISTS `brokers_app_categorymaster`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_categorymaster` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `category_name` varchar(100) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `level` int unsigned NOT NULL,
  `parent_id` bigint DEFAULT NULL,
  `path` varchar(500) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `brokers_app_category_parent_id_8d54114d_fk_brokers_a` (`parent_id`),
  CONSTRAINT `brokers_app_category_parent_id_8d54114d_fk_brokers_a` FOREIGN KEY (`parent_id`) REFERENCES `brokers_app_categorymaster` (`id`),
  CONSTRAINT `brokers_app_categorymaster_chk_1` CHECK ((`level` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_categorymaster`
--

LOCK TABLES `brokers_app_categorymaster` WRITE;
/*!40000 ALTER TABLE `brokers_app_categorymaster` DISABLE KEYS */;
INSERT INTO `brokers_app_categorymaster` VALUES (1,'Masoor Daal','2026-02-09 07:02:17.945276','2026-02-19 07:08:48.708172',1,0,NULL,''),(2,'Moong Dal','2026-02-09 07:22:30.496208','2026-02-19 07:03:34.462187',1,0,NULL,''),(3,'Chickpea','2026-02-19 07:10:10.388012','2026-02-19 07:10:10.388056',1,0,NULL,''),(4,'Fenugreak(Methi)','2026-02-19 07:12:09.684911','2026-02-19 07:12:09.684950',1,0,NULL,''),(5,'Chole','2026-02-19 07:13:49.586238','2026-02-19 07:13:49.586276',1,0,NULL,''),(6,'Kabuli Chana','2026-02-19 12:22:20.402857','2026-02-19 12:22:20.402896',1,0,NULL,''),(7,'Edible seeds','2026-02-20 05:21:58.167849','2026-02-20 05:21:58.167886',1,0,NULL,''),(8,'Rice1','2026-02-20 10:53:39.643263','2026-02-20 10:53:39.643305',1,0,NULL,''),(9,'Rice2','2026-02-20 15:55:33.296419','2026-02-20 15:55:33.296452',1,0,NULL,''),(10,'moong dal','2026-02-25 12:49:07.910876','2026-02-25 12:49:07.910919',1,1,4,'10/');
/*!40000 ALTER TABLE `brokers_app_categorymaster` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_contract`
--

DROP TABLE IF EXISTS `brokers_app_contract`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_contract` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `contract_id` varchar(20) NOT NULL,
  `deal_amount` decimal(12,2) NOT NULL,
  `deal_quantity` decimal(12,2) NOT NULL,
  `amount_unit` varchar(10) NOT NULL,
  `quantity_unit` varchar(10) NOT NULL,
  `loading_from` varchar(200) NOT NULL,
  `loading_to` varchar(200) NOT NULL,
  `buyer_remark` longtext,
  `seller_remark` longtext,
  `admin_remark` longtext,
  `confirmed_at` datetime(6) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `status` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `contract_id` (`contract_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_contract`
--

LOCK TABLES `brokers_app_contract` WRITE;
/*!40000 ALTER TABLE `brokers_app_contract` DISABLE KEYS */;
/*!40000 ALTER TABLE `brokers_app_contract` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_daaluser`
--

DROP TABLE IF EXISTS `brokers_app_daaluser`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_daaluser` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `username` varchar(100) NOT NULL,
  `first_name` varchar(100) DEFAULT NULL,
  `last_name` varchar(100) DEFAULT NULL,
  `email` varchar(254) DEFAULT NULL,
  `mobile` varchar(15) NOT NULL,
  `is_buyer` tinyint(1) NOT NULL,
  `is_seller` tinyint(1) NOT NULL,
  `is_admin` tinyint(1) NOT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `is_transporter` tinyint(1) NOT NULL,
  `char_password` varchar(128) DEFAULT NULL,
  `gst_number` varchar(15) DEFAULT NULL,
  `is_both_sellerandbuyer` tinyint(1) NOT NULL,
  `pan_number` varchar(10) DEFAULT NULL,
  `role` varchar(20) NOT NULL,
  `brand` varchar(200) DEFAULT NULL,
  `company_name` varchar(200) DEFAULT NULL,
  `dob` date DEFAULT NULL,
  `gst_image` varchar(100) DEFAULT NULL,
  `kyc_status` varchar(20) NOT NULL,
  `pan_image` varchar(100) DEFAULT NULL,
  `status` varchar(20) NOT NULL,
  `account_status` varchar(20) NOT NULL,
  `deactivated_at` datetime(6) DEFAULT NULL,
  `gender` varchar(10) DEFAULT NULL,
  `kyc_approved_at` datetime(6) DEFAULT NULL,
  `kyc_rejected_at` datetime(6) DEFAULT NULL,
  `kyc_rejection_reason` longtext,
  `kyc_submitted_at` datetime(6) DEFAULT NULL,
  `profile_image` varchar(100) DEFAULT NULL,
  `suspended_at` datetime(6) DEFAULT NULL,
  `suspension_reason` longtext,
  `adharcard_image` varchar(100) DEFAULT NULL,
  `buyer_unique_id` varchar(20) DEFAULT NULL,
  `shopact_image` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `mobile` (`mobile`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `buyer_unique_id` (`buyer_unique_id`),
  KEY `brokers_app_daaluser_account_status_ae00d94f` (`account_status`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_daaluser`
--

LOCK TABLES `brokers_app_daaluser` WRITE;
/*!40000 ALTER TABLE `brokers_app_daaluser` DISABLE KEYS */;
INSERT INTO `brokers_app_daaluser` VALUES (1,'pbkdf2_sha256$1200000$5FTd5JLAJulZXhfPlrKuGD$7GBl5qSpe67qvYsrofYFPHn6iqWqlGRUuezApikkFuI=','2026-02-19 05:52:28.012129','1234567890','aparna',NULL,'aparnabhajbhuje@gmail.com','1234567890',0,0,0,1,0,1,'2026-02-04 07:28:11.000000',0,NULL,NULL,0,NULL,'buyer',NULL,NULL,NULL,'','rejected','','active','active',NULL,NULL,NULL,'2026-02-18 10:19:52.211825','Send Your Proper details','2026-02-18 10:15:05.970368','profile/luffy-laughing-one-3840x2160-12358.png',NULL,'',NULL,NULL,NULL),(2,'pbkdf2_sha256$1200000$2v2Pg1kOxMlMkAF1o4W15K$EJypQBJTc/DGs71xhVvYLet9y1QBvls8DbV9wDwwAiQ=','2026-02-20 15:41:04.817581','9993949080','Buyer','one','buyer01@gmail.com','9993949080',1,0,0,0,0,1,'2026-02-04 08:55:46.000000',0,'admin','27AAACM3025E1ZZ',0,'PAN0012345','buyer',NULL,NULL,NULL,'','approved','','active','active',NULL,NULL,'2026-02-18 05:39:42.889252',NULL,'','2026-02-17 12:00:49.000000','',NULL,'',NULL,NULL,NULL),(3,'pbkdf2_sha256$1200000$RwkJqbI94T2yW6KYk7aSs3$togH0+DYcs3W64mxWVJlkGC6M9mwsqIa44LyVOtHfzg=','2026-02-20 15:36:31.963657','9993949081','Seller','one','nisharmeshram199@gmail.com','9993949081',0,1,0,0,0,1,'2026-02-04 08:58:23.000000',0,'admin','27AAACM3025E1ZZ',0,'PAN0012345','seller',NULL,NULL,NULL,'','approved','','active','active',NULL,NULL,'2026-02-20 15:53:14.870414',NULL,'','2026-02-17 10:51:09.000000','profile/photos.jpeg',NULL,'',NULL,NULL,NULL),(4,'pbkdf2_sha256$1200000$kHmPdM1vDV6XtqQSRDYr6b$KXXAkau5ijbBFd4eAFkxB5kLt3OkOSjlNTWyA4unC90=','2026-02-20 15:39:36.798393','9993949082','transporter','one','transporter012gmail.com','9993949082',0,0,0,0,0,1,'2026-02-04 09:00:19.505776',1,'admin','27AAACM3025E1ZE',0,'PAN0012346','transporter',NULL,NULL,NULL,NULL,'approved',NULL,'active','active',NULL,NULL,'2026-02-17 10:16:41.827308',NULL,'','2026-02-17 10:16:41.826060',NULL,NULL,NULL,NULL,NULL,NULL),(5,'pbkdf2_sha256$1200000$RPxQxF4kXkfHY9N8M1UyyY$v/lsJv6pgJzc09B6OuYLuc7L2suouroxleqvuoZM0jg=','2026-02-11 04:59:49.197104','9993949083','Buyer','Seller','buyerandseller01@gmail.com','9993949083',1,1,0,0,0,1,'2026-02-05 14:00:00.324550',0,'admin','27AAACM3025H6ZZ',1,'PAN0012367','both_sellerandbuyer',NULL,NULL,NULL,NULL,'approved',NULL,'active','active',NULL,NULL,'2026-02-17 10:06:43.691140',NULL,'','2026-02-17 10:06:43.654272',NULL,NULL,NULL,NULL,NULL,NULL),(8,'pbkdf2_sha256$1200000$xFY0NftaNiKjctNKDw7NkM$53ZrtRwBIYmI2l0n7+LEcfkJEIDwQ3sPlRuIGjyzsFE=','2026-02-20 08:02:43.586268','07974130626','Muskan','Patil','muskanpatil2004@gmail.com','07974130626',1,0,0,0,0,1,'2026-02-17 07:48:46.184919',0,'12345','37ABCDG1234H2Z5',0,'ABCDG1234H','buyer',NULL,NULL,NULL,'','approved','','active','active',NULL,NULL,'2026-02-20 08:04:20.976127',NULL,'','2026-02-17 10:27:55.669937','',NULL,'',NULL,NULL,NULL),(10,'pbkdf2_sha256$1200000$bCb88EA3OiqsJJuBpZ5pZe$fD6+kdxKC/Ae1B0Bv2rYJ+ah4aFq8FvtXOUVa7tVs2Y=','2026-02-20 14:52:49.000000','daalbroker','Daal',NULL,'daalsetu@gmail.com','1234567899',0,0,1,1,1,1,'2026-02-17 10:45:17.000000',0,'admin@123',NULL,0,NULL,'admin',NULL,NULL,NULL,'','approved','','active','active',NULL,NULL,'2026-02-19 07:00:51.000000',NULL,'','2026-02-19 07:00:51.000000','profile/WhatsApp_Image_2026-02-18_at_11_mKO7wq9.55.34_AM.jpeg',NULL,'',NULL,NULL,NULL),(11,'pbkdf2_sha256$1200000$59jm3d4PGgtsDO1SvnsmpQ$qRpkUN4RkdwB+re826RBlwN/vVKeBuMo8roeaQwVhQE=','2026-02-25 07:56:46.441343','1234512345','Priti','Sharnagat','pritisharnagat4@gmail.com','1234512345',0,1,0,0,0,1,'2026-02-18 05:17:04.237773',0,'admin','',0,'','seller',NULL,NULL,NULL,'','approved','','active','active',NULL,NULL,'2026-02-19 07:00:53.748068',NULL,'','2026-02-19 07:00:53.748060','',NULL,'',NULL,NULL,NULL),(12,'pbkdf2_sha256$1200000$JIo1ZKB0SVRlWv24O76VH6$OrNM0vxf8QZwSUMw7wr3TuABBmeTaEp6SVBTztsgf7I=',NULL,'7999840592','Prem','Verma','premv6264@gmail.com','7999840592',0,0,1,0,1,1,'2026-02-18 09:16:50.550637',0,'4yr%Dz&Z','29ABCDE1235F1Z5',0,'ABCDE1235F','admin',NULL,NULL,'2025-12-25','gst_images/naruro_wallpepar.jpeg','pending','pan_images/download_2.jpg','active','active',NULL,'male',NULL,NULL,'','2026-02-18 09:16:50.550424','',NULL,NULL,NULL,NULL,NULL),(13,'pbkdf2_sha256$1200000$Xns33ZoBGO3Tzv6Yf3QrDx$Rik6YtpmKR5WoRtrUdgSd9B/GkR34/UwGNpz2KAzbk4=',NULL,'9575760696','Adarsh','ZappKOde','worksspace2512@gmail.com','9575760696',0,1,0,0,0,1,'2026-02-18 09:47:14.009709',0,'adar@696','18ABCDE1234E1Z0',0,'ABCDE1234E','seller',NULL,NULL,'2019-12-02','','approved','','active','active',NULL,'male','2026-02-20 09:15:22.961669',NULL,'','2026-02-18 09:47:14.009564','',NULL,NULL,NULL,NULL,NULL),(14,'pbkdf2_sha256$1200000$YyDRZNF6XTuEFGwQ0rFnJo$Gm+zYTZQrK+CWMAZzHQsObQQE8PDx05oe3EuFeL5K9I=',NULL,'9325378754','Prem','Verma','premv6764@gmail.com','9325378754',0,0,1,0,1,1,'2026-02-19 05:49:59.887312',0,'prem@754','29ABCDE1235H1Z5',0,'ABCDE1235H','admin',NULL,NULL,'2025-12-25','gst_images/Dwonload-the-hd-1mb-pink-hair-girl-image.webp','pending','pan_images/OIP.jpeg','active','active',NULL,'male',NULL,NULL,'','2026-02-19 05:49:59.886961','',NULL,NULL,NULL,NULL,NULL),(18,'pbkdf2_sha256$1200000$sIoYSISAWzIUD79SRgP8WY$QGak9DOF2jUSmkmas/VnlfIfIWQcZIF1cK3kMjbg510=','2026-02-20 10:12:39.785717','9881886261','Siddhi','Atkare','siddatkare@gmail.com','9881886261',1,0,0,0,0,1,'2026-02-19 06:56:12.661750',0,'Sidd@123','',0,'','buyer',NULL,NULL,NULL,'','approved','','active','active',NULL,NULL,'2026-02-19 12:15:31.619312',NULL,'','2026-02-19 06:59:44.259977','',NULL,'',NULL,NULL,NULL),(19,'pbkdf2_sha256$1200000$4KYYFLwNLKRM1NzSvzFSNm$4g5BU8yMJ8fqD3lic4kAU//CmrZaRNiA4mf6zKfaE/I=',NULL,'9325371176','Kanhaiya','Gore','kmgore45@gmail.com','9325371176',0,0,1,0,1,1,'2026-02-19 09:44:58.537037',0,'kanh@176','23DOEPG8576Y1Z5',0,'DOEPG8576Y','admin',NULL,NULL,'2000-01-01','gst_images/112972_ZkBpOyf.jpg','pending','pan_images/112972_NIVnt1s.jpg','active','active',NULL,'male',NULL,NULL,'','2026-02-19 09:44:58.536919','',NULL,NULL,NULL,NULL,NULL),(20,'pbkdf2_sha256$1200000$8MiOjoQr6qDwBew62kB182$mh1vQ4giezlrQ15LbGSh+cvQbwjWnKPlPGBs0l7iJgc=',NULL,'9546319431','Kanhaiya','Gore','kanhaiyagore71@gmail.com','9546319431',0,1,0,0,0,1,'2026-02-20 13:21:00.578448',0,'kanh@431','',0,'','seller',NULL,NULL,NULL,'gst_images/114118.jpg','pending','pan_images/114118.jpg','active','active',NULL,'male',NULL,NULL,'','2026-02-20 13:21:00.578242','',NULL,NULL,NULL,NULL,NULL),(21,'pbkdf2_sha256$1200000$5MHUzh38FXk6rSLS9uvXoD$EkPuBKQB+11raERSDj2eeLH/w4UHy3drvfcMId18obU=',NULL,'9325376196','kanhaiya','gore','kmgore4565@gmail.com','9325376196',0,1,0,0,0,1,'2026-02-20 13:24:44.720015',0,'kanh@196','',0,'','seller',NULL,NULL,NULL,'gst_images/114118_QYL9qaK.jpg','rejected','pan_images/114118_hxEvABV.jpg','active','active',NULL,'male',NULL,'2026-02-20 13:51:19.969570','h j j j onononon','2026-02-20 13:24:44.719881','',NULL,NULL,NULL,NULL,NULL),(22,'pbkdf2_sha256$1200000$JDIyQEPYx7VV7Ep9YWwM1Y$G92uL8kI6ghpma10d0V5CYbE4Dy1vdPHhWggbcSc2hg=',NULL,'6261374339','Nishar','Meshram','nisharmesharam.cse20@ggct.co.in','6261374339',0,0,1,0,1,1,'2026-02-20 14:53:25.284324',0,'123123','',0,'','admin',NULL,NULL,NULL,'','pending','','active','active',NULL,NULL,NULL,NULL,NULL,NULL,'',NULL,'',NULL,NULL,NULL),(23,'pbkdf2_sha256$1200000$PAlQ4Eu4JXHZAIj7ZRCOoM$WjCsPa/UGrX12n1AxH6LZGintbccpiraAtxfsv4z9NQ=',NULL,'09993949081','nishar','Meshram','nisharmesharam.cse520@ggct.co.in','09993949081',1,0,0,0,0,1,'2026-02-20 15:44:56.513394',0,'admin','',0,'','buyer',NULL,NULL,NULL,'','approved','','active','active',NULL,NULL,'2026-02-20 15:46:21.871537',NULL,'','2026-02-20 15:46:21.871529','',NULL,'',NULL,NULL,NULL),(24,'pbkdf2_sha256$1200000$8cU83RjwuZX2GnPsIfiWNK$KLm96AcZu2yc8d1kj8Ms8fID3AMNNR+Fjd9XJYBrGyE=','2026-02-25 07:55:24.133938','1234567891','Register','Seller','seller@gmail.com','1234567891',1,0,0,0,0,1,'2026-02-22 17:33:55.045083',0,'regi@891','29ABCDE1235Z1Z5',0,'ABCDE1235Z','buyer',NULL,NULL,'2025-12-25','gst_images/zenlessace_14041128_094315835.jpg.jpeg','pending','pan_images/KING.jpeg','active','active',NULL,'male',NULL,NULL,'','2026-02-22 17:33:55.044924','',NULL,NULL,NULL,NULL,NULL);
/*!40000 ALTER TABLE `brokers_app_daaluser` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_daaluser_groups`
--

DROP TABLE IF EXISTS `brokers_app_daaluser_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_daaluser_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `daaluser_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `brokers_app_daaluser_groups_daaluser_id_group_id_d01de09e_uniq` (`daaluser_id`,`group_id`),
  KEY `brokers_app_daaluser_groups_group_id_ec13e4d9_fk_auth_group_id` (`group_id`),
  CONSTRAINT `brokers_app_daaluser_daaluser_id_c976bdcb_fk_brokers_a` FOREIGN KEY (`daaluser_id`) REFERENCES `brokers_app_daaluser` (`id`),
  CONSTRAINT `brokers_app_daaluser_groups_group_id_ec13e4d9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_daaluser_groups`
--

LOCK TABLES `brokers_app_daaluser_groups` WRITE;
/*!40000 ALTER TABLE `brokers_app_daaluser_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `brokers_app_daaluser_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_daaluser_tags`
--

DROP TABLE IF EXISTS `brokers_app_daaluser_tags`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_daaluser_tags` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `daaluser_id` bigint NOT NULL,
  `tagmaster_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_tag` (`daaluser_id`,`tagmaster_id`),
  KEY `tagmaster_id` (`tagmaster_id`),
  CONSTRAINT `brokers_app_daaluser_tags_ibfk_1` FOREIGN KEY (`daaluser_id`) REFERENCES `brokers_app_daaluser` (`id`) ON DELETE CASCADE,
  CONSTRAINT `brokers_app_daaluser_tags_ibfk_2` FOREIGN KEY (`tagmaster_id`) REFERENCES `brokers_app_tagmaster` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_daaluser_tags`
--

LOCK TABLES `brokers_app_daaluser_tags` WRITE;
/*!40000 ALTER TABLE `brokers_app_daaluser_tags` DISABLE KEYS */;
/*!40000 ALTER TABLE `brokers_app_daaluser_tags` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_daaluser_user_permissions`
--

DROP TABLE IF EXISTS `brokers_app_daaluser_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_daaluser_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `daaluser_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `brokers_app_daaluser_use_daaluser_id_permission_i_efc4cc96_uniq` (`daaluser_id`,`permission_id`),
  KEY `brokers_app_daaluser_permission_id_6b4c83b2_fk_auth_perm` (`permission_id`),
  CONSTRAINT `brokers_app_daaluser_daaluser_id_4b704970_fk_brokers_a` FOREIGN KEY (`daaluser_id`) REFERENCES `brokers_app_daaluser` (`id`),
  CONSTRAINT `brokers_app_daaluser_permission_id_6b4c83b2_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_daaluser_user_permissions`
--

LOCK TABLES `brokers_app_daaluser_user_permissions` WRITE;
/*!40000 ALTER TABLE `brokers_app_daaluser_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `brokers_app_daaluser_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_polishmaster`
--

DROP TABLE IF EXISTS `brokers_app_polishmaster`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_polishmaster` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `polish_name` varchar(100) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_polishmaster`
--

LOCK TABLES `brokers_app_polishmaster` WRITE;
/*!40000 ALTER TABLE `brokers_app_polishmaster` DISABLE KEYS */;
INSERT INTO `brokers_app_polishmaster` VALUES (1,'Un-Polish','2026-02-09 07:03:39.298346','2026-02-19 07:30:05.297955'),(2,'Polish','2026-02-19 07:29:22.611092','2026-02-19 07:29:40.061268');
/*!40000 ALTER TABLE `brokers_app_polishmaster` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_product`
--

DROP TABLE IF EXISTS `brokers_app_product`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_product` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `description` longtext,
  `loading_location` varchar(200) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `category_id` bigint NOT NULL,
  `root_category_id` bigint DEFAULT NULL,
  `category_path` longtext,
  `brand_id` bigint DEFAULT NULL,
  `seller_id` bigint NOT NULL,
  `amount` decimal(10,2) DEFAULT '0.00',
  `amount_unit` varchar(10) DEFAULT 'kg',
  `original_quantity` decimal(10,2) DEFAULT NULL,
  `remaining_quantity` decimal(10,2) DEFAULT NULL,
  `quantity_unit` varchar(10) DEFAULT 'kg',
  `loading_from` varchar(200) DEFAULT NULL,
  `loading_to` varchar(200) DEFAULT NULL,
  `remark` longtext,
  `deal_status` varchar(30) NOT NULL,
  `is_approved` tinyint(1) NOT NULL,
  `status` varchar(40) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `brokers_app_product_category_id_c9b1b88d_fk_brokers_a` (`category_id`),
  KEY `brokers_app_product_seller_id_97b409e2_fk_brokers_a` (`seller_id`),
  KEY `brokers_app_product_deal_status_bb57d763` (`deal_status`),
  KEY `brokers_app_product_status_1c153a65` (`status`),
  KEY `brokers_app_product_root_category_idx` (`root_category_id`),
  KEY `brokers_app_product_brand_idx` (`brand_id`),
  KEY `brokers_app_product_status_idx` (`status`),
  KEY `brokers_app_product_deal_status_idx` (`deal_status`),
  CONSTRAINT `brokers_app_product_category_id_c9b1b88d_fk_brokers_a` FOREIGN KEY (`category_id`) REFERENCES `brokers_app_categorymaster` (`id`),
  CONSTRAINT `brokers_app_product_seller_id_97b409e2_fk_brokers_a` FOREIGN KEY (`seller_id`) REFERENCES `brokers_app_daaluser` (`id`),
  CONSTRAINT `fk_product_brand` FOREIGN KEY (`brand_id`) REFERENCES `brokers_app_brandmaster` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_product_root_category` FOREIGN KEY (`root_category_id`) REFERENCES `brokers_app_categorymaster` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_product`
--

LOCK TABLES `brokers_app_product` WRITE;
/*!40000 ALTER TABLE `brokers_app_product` DISABLE KEYS */;
INSERT INTO `brokers_app_product` VALUES (4,'Moong','Organic Daal from direct Farm','Nagpur',0,'2026-02-19 07:37:29.234112','2026-02-20 12:11:13.388381',2,NULL,NULL,NULL,11,0.00,'kg',NULL,NULL,'kg',NULL,NULL,NULL,'deal_confirmed',0,'sold'),(5,'Methi','Direct from Organic Farm','Yavatmal',0,'2026-02-19 07:38:43.145405','2026-02-20 05:08:55.419769',4,NULL,NULL,NULL,3,0.00,'kg',NULL,NULL,'kg',NULL,NULL,NULL,'deal_confirmed',0,'sold'),(6,'chia seeds','organic seeds','Nagpur',0,'2026-02-20 05:38:37.533103','2026-02-20 10:12:51.746717',7,NULL,NULL,NULL,3,0.00,'kg',NULL,NULL,'kg',NULL,NULL,NULL,'deal_confirmed',0,'sold'),(7,'sabja seeds','organic seeds','Nagpur',0,'2026-02-20 05:39:43.383115','2026-02-20 09:22:14.051931',7,NULL,NULL,NULL,3,0.00,'kg',NULL,NULL,'kg',NULL,NULL,NULL,'deal_confirmed',0,'sold'),(10,'White rice','','Nagpur',1,'2026-02-20 10:55:37.065239','2026-02-20 16:53:13.455409',8,NULL,NULL,NULL,3,0.00,'kg',NULL,NULL,'kg',NULL,NULL,NULL,'seller_confirmed',0,'sold_pending_confirmation'),(11,'Rice','','Nagpur',0,'2026-02-20 16:04:25.366828','2026-02-20 16:53:44.241936',9,NULL,NULL,NULL,3,0.00,'kg',NULL,NULL,'kg',NULL,NULL,NULL,'deal_confirmed',0,'sold');
/*!40000 ALTER TABLE `brokers_app_product` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_productimage`
--

DROP TABLE IF EXISTS `brokers_app_productimage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_productimage` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `image` varchar(100) NOT NULL,
  `is_primary` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `product_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `brokers_app_producti_product_id_8e939f6d_fk_brokers_a` (`product_id`),
  CONSTRAINT `brokers_app_producti_product_id_8e939f6d_fk_brokers_a` FOREIGN KEY (`product_id`) REFERENCES `brokers_app_product` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_productimage`
--

LOCK TABLES `brokers_app_productimage` WRITE;
/*!40000 ALTER TABLE `brokers_app_productimage` DISABLE KEYS */;
INSERT INTO `brokers_app_productimage` VALUES (2,'product_images/shopping.webp',1,'2026-02-19 07:39:44.841388',5);
/*!40000 ALTER TABLE `brokers_app_productimage` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_productinterest`
--

DROP TABLE IF EXISTS `brokers_app_productinterest`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_productinterest` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `is_active` tinyint(1) NOT NULL,
  `status` varchar(20) NOT NULL,
  `delivery_date` date DEFAULT NULL,
  `deal_confirmed_at` datetime DEFAULT NULL,
  `negotiation_history` json DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `buyer_id` bigint NOT NULL,
  `product_id` bigint NOT NULL,
  `seller_id` bigint NOT NULL,
  `snapshot_amount` decimal(12,2) DEFAULT NULL,
  `snapshot_quantity` decimal(12,2) DEFAULT NULL,
  `buyer_offered_amount` decimal(12,2) DEFAULT NULL,
  `buyer_required_quantity` decimal(12,2) DEFAULT '1.00',
  `loading_from` varchar(200) DEFAULT NULL,
  `loading_to` varchar(200) DEFAULT NULL,
  `buyer_remark` longtext,
  `seller_remark` longtext,
  `superadmin_remark` longtext,
  `transaction_id` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `transaction_id` (`transaction_id`),
  KEY `brokers_app_product_43db2c_idx` (`product_id`,`status`),
  KEY `brokers_app_seller__f1b19d_idx` (`seller_id`,`status`),
  KEY `brokers_app_buyer_i_4cf72b_idx` (`buyer_id`,`status`),
  KEY `brokers_app_productinterest_is_active_eb69d7e8` (`is_active`),
  KEY `brokers_app_productinterest_status_c211799b` (`status`),
  KEY `brokers_app_productinterest_created_at_8520d280` (`created_at`),
  CONSTRAINT `brokers_app_producti_buyer_id_2e6d167d_fk_brokers_a` FOREIGN KEY (`buyer_id`) REFERENCES `brokers_app_daaluser` (`id`),
  CONSTRAINT `brokers_app_producti_product_id_b0cc29f7_fk_brokers_a` FOREIGN KEY (`product_id`) REFERENCES `brokers_app_product` (`id`),
  CONSTRAINT `brokers_app_producti_seller_id_6995167f_fk_brokers_a` FOREIGN KEY (`seller_id`) REFERENCES `brokers_app_daaluser` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_productinterest`
--

LOCK TABLES `brokers_app_productinterest` WRITE;
/*!40000 ALTER TABLE `brokers_app_productinterest` DISABLE KEYS */;
INSERT INTO `brokers_app_productinterest` VALUES (3,1,'deal_confirmed',NULL,NULL,NULL,'2026-02-19 12:25:42.962975','2026-02-20 05:08:55.407429',18,5,3,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL),(4,1,'deal_confirmed',NULL,NULL,NULL,'2026-02-19 12:26:35.152709','2026-02-20 12:11:13.381766',18,4,11,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL),(5,1,'deal_confirmed',NULL,NULL,NULL,'2026-02-20 06:03:36.673764','2026-02-20 10:12:51.736289',18,6,3,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL),(6,0,'interested',NULL,NULL,NULL,'2026-02-20 07:05:00.218499','2026-02-20 07:08:48.168164',18,7,3,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL),(8,0,'interested',NULL,NULL,NULL,'2026-02-20 07:39:57.401427','2026-02-20 07:39:58.764624',10,7,3,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL),(9,0,'interested',NULL,NULL,NULL,'2026-02-20 07:40:53.889367','2026-02-20 10:01:12.989441',10,6,3,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL),(10,0,'interested',NULL,NULL,NULL,'2026-02-20 07:41:06.697693','2026-02-20 07:41:08.384339',10,4,11,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL),(11,0,'interested',NULL,NULL,NULL,'2026-02-20 08:06:28.871866','2026-02-20 10:10:12.420931',8,6,3,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL),(12,1,'deal_confirmed',NULL,NULL,NULL,'2026-02-20 08:06:33.119006','2026-02-20 09:22:14.030560',8,7,3,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL),(13,0,'interested',NULL,NULL,NULL,'2026-02-20 08:06:38.528751','2026-02-20 08:17:37.204244',8,4,11,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL),(14,1,'interested',NULL,NULL,NULL,'2026-02-20 10:56:46.485290','2026-02-20 10:56:56.864156',1,10,3,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL),(15,0,'interested',NULL,NULL,NULL,'2026-02-20 12:13:48.497693','2026-02-20 12:14:05.157491',18,10,3,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL),(16,1,'seller_confirmed',NULL,NULL,NULL,'2026-02-20 13:55:21.268882','2026-02-20 13:55:21.268913',10,10,3,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL),(17,1,'deal_confirmed',NULL,NULL,NULL,'2026-02-20 16:04:50.757435','2026-02-20 16:53:44.226448',2,11,3,NULL,NULL,NULL,1.00,NULL,NULL,NULL,NULL,NULL,NULL);
/*!40000 ALTER TABLE `brokers_app_productinterest` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_productvideo`
--

DROP TABLE IF EXISTS `brokers_app_productvideo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_productvideo` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `video` varchar(100) NOT NULL,
  `title` varchar(200) DEFAULT NULL,
  `is_primary` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `product_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `brokers_app_productv_product_id_6c3313c3_fk_brokers_a` (`product_id`),
  CONSTRAINT `brokers_app_productv_product_id_6c3313c3_fk_brokers_a` FOREIGN KEY (`product_id`) REFERENCES `brokers_app_product` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_productvideo`
--

LOCK TABLES `brokers_app_productvideo` WRITE;
/*!40000 ALTER TABLE `brokers_app_productvideo` DISABLE KEYS */;
/*!40000 ALTER TABLE `brokers_app_productvideo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_rolepermission`
--

DROP TABLE IF EXISTS `brokers_app_rolepermission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_rolepermission` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `role` varchar(20) NOT NULL,
  `module` varchar(50) NOT NULL,
  `action` varchar(10) NOT NULL,
  `is_allowed` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `brokers_app_rolepermission_role_module_action_8d4d788c_uniq` (`role`,`module`,`action`)
) ENGINE=InnoDB AUTO_INCREMENT=101 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_rolepermission`
--

LOCK TABLES `brokers_app_rolepermission` WRITE;
/*!40000 ALTER TABLE `brokers_app_rolepermission` DISABLE KEYS */;
INSERT INTO `brokers_app_rolepermission` VALUES (1,'admin','user_management','create',1,'2026-02-04 19:47:38.249287','2026-02-19 09:47:55.869075'),(2,'buyer','user_management','create',1,'2026-02-04 19:50:35.111592','2026-02-20 05:24:20.721508'),(3,'buyer','user_management','read',1,'2026-02-04 19:50:35.620446','2026-02-20 05:24:20.789431'),(4,'buyer','user_management','update',1,'2026-02-04 19:50:36.686116','2026-02-20 05:24:20.860085'),(5,'buyer','user_management','delete',1,'2026-02-04 19:50:37.207184','2026-02-20 05:24:20.934177'),(6,'buyer','category_management','create',1,'2026-02-04 19:50:37.566392','2026-02-20 05:24:21.299588'),(7,'buyer','category_management','read',1,'2026-02-04 19:50:38.088400','2026-02-20 05:24:21.368775'),(8,'buyer','category_management','update',1,'2026-02-04 19:50:38.509737','2026-02-20 05:24:21.440407'),(9,'buyer','category_management','delete',1,'2026-02-04 19:50:39.358772','2026-02-20 05:24:21.513519'),(10,'buyer','subcategory_management','create',1,'2026-02-04 19:50:39.767962','2026-02-20 05:24:21.584314'),(11,'buyer','subcategory_management','read',1,'2026-02-04 19:50:40.582050','2026-02-20 05:24:21.651391'),(12,'buyer','subcategory_management','update',1,'2026-02-04 19:50:41.199960','2026-02-20 05:24:21.725887'),(13,'buyer','subcategory_management','delete',1,'2026-02-04 19:50:42.931245','2026-02-20 05:24:21.802788'),(14,'buyer','polish_management','create',1,'2026-02-04 19:50:43.388972','2026-02-20 05:24:21.874320'),(15,'buyer','polish_management','read',1,'2026-02-04 19:50:43.789864','2026-02-20 05:24:21.943200'),(16,'buyer','polish_management','update',1,'2026-02-04 19:50:44.235004','2026-02-20 05:24:22.009484'),(17,'buyer','polish_management','delete',1,'2026-02-04 19:50:44.675967','2026-02-20 05:24:22.079538'),(18,'buyer','product_management','create',1,'2026-02-04 19:50:46.578456','2026-02-20 05:24:22.150132'),(19,'buyer','product_management','read',1,'2026-02-04 19:50:47.042070','2026-02-20 05:24:22.224891'),(20,'buyer','product_management','update',1,'2026-02-04 19:50:47.712683','2026-02-20 05:24:22.299177'),(21,'buyer','product_management','delete',1,'2026-02-04 19:50:48.285302','2026-02-20 05:24:22.370433'),(22,'buyer','product_image_management','create',1,'2026-02-04 19:50:49.693032','2026-02-20 05:24:22.443321'),(23,'buyer','product_image_management','read',1,'2026-02-04 19:50:50.188806','2026-02-20 05:24:22.514169'),(24,'buyer','product_image_management','update',1,'2026-02-04 19:50:50.747481','2026-02-20 05:24:22.584735'),(25,'buyer','product_image_management','delete',1,'2026-02-04 19:50:51.818652','2026-02-20 05:24:22.653827'),(26,'admin','user_management','read',1,'2026-02-04 19:53:49.289263','2026-02-19 09:47:55.936922'),(27,'admin','user_management','update',1,'2026-02-04 19:53:49.764771','2026-02-19 09:47:56.008701'),(28,'admin','user_management','delete',1,'2026-02-04 19:53:50.254902','2026-02-19 09:47:56.090365'),(29,'admin','category_management','create',1,'2026-02-04 19:53:50.920186','2026-02-19 09:47:56.487479'),(30,'admin','category_management','update',1,'2026-02-04 19:53:52.003041','2026-02-19 09:47:56.653626'),(31,'admin','category_management','read',1,'2026-02-04 19:53:52.476564','2026-02-19 09:47:56.569247'),(32,'admin','category_management','delete',1,'2026-02-04 19:53:53.062850','2026-02-19 09:47:56.739518'),(33,'admin','subcategory_management','create',1,'2026-02-04 19:53:53.643698','2026-02-19 09:47:56.826658'),(34,'admin','subcategory_management','read',1,'2026-02-04 19:53:54.646206','2026-02-19 09:47:56.907481'),(35,'admin','subcategory_management','update',1,'2026-02-04 19:53:55.110534','2026-02-19 09:47:56.985851'),(36,'admin','subcategory_management','delete',0,'2026-02-04 19:53:55.601834','2026-02-20 16:50:57.638335'),(37,'seller','subcategory_management','delete',1,'2026-02-04 19:53:56.704439','2026-02-20 04:58:08.399459'),(38,'seller','subcategory_management','update',1,'2026-02-04 19:53:57.539042','2026-02-20 04:58:08.331067'),(39,'seller','subcategory_management','read',1,'2026-02-04 19:53:58.193742','2026-02-20 04:58:08.261835'),(40,'seller','subcategory_management','create',1,'2026-02-04 19:53:58.853265','2026-02-20 04:58:08.198276'),(41,'seller','category_management','delete',1,'2026-02-04 19:53:59.506065','2026-02-20 04:58:08.133587'),(42,'seller','category_management','update',1,'2026-02-04 19:54:00.200331','2026-02-20 04:58:08.071910'),(43,'seller','category_management','create',1,'2026-02-04 19:54:01.598813','2026-02-20 04:58:07.940957'),(44,'seller','user_management','delete',1,'2026-02-04 19:54:02.813081','2026-02-20 04:58:07.608179'),(45,'seller','user_management','update',1,'2026-02-04 19:54:03.529362','2026-02-20 04:58:07.532920'),(46,'seller','user_management','create',1,'2026-02-04 19:54:04.910129','2026-02-20 04:58:07.399456'),(47,'seller','user_management','read',1,'2026-02-04 19:54:06.319018','2026-02-20 04:58:07.469916'),(48,'seller','category_management','read',1,'2026-02-04 19:54:07.647947','2026-02-20 04:58:08.008076'),(49,'transporter','user_management','create',1,'2026-02-04 19:54:08.906764','2026-02-04 19:54:08.906960'),(50,'transporter','user_management','read',1,'2026-02-04 19:54:09.384782','2026-02-04 19:54:09.385015'),(51,'transporter','user_management','update',1,'2026-02-04 19:54:09.988492','2026-02-04 19:54:09.988697'),(52,'transporter','user_management','delete',1,'2026-02-04 19:54:10.626287','2026-02-04 19:54:10.626814'),(53,'transporter','category_management','create',1,'2026-02-04 19:54:11.166330','2026-02-04 19:54:11.166569'),(54,'transporter','category_management','read',1,'2026-02-04 19:54:11.641489','2026-02-04 19:54:11.641757'),(55,'transporter','category_management','update',1,'2026-02-04 19:54:12.172223','2026-02-04 19:54:12.172527'),(56,'transporter','category_management','delete',1,'2026-02-04 19:54:12.877295','2026-02-04 19:54:12.877480'),(57,'transporter','subcategory_management','create',1,'2026-02-04 19:54:13.582937','2026-02-04 19:54:13.583200'),(58,'transporter','subcategory_management','read',1,'2026-02-04 19:54:14.329730','2026-02-04 19:54:14.330346'),(59,'transporter','subcategory_management','update',1,'2026-02-04 19:54:14.964154','2026-02-04 19:54:14.964327'),(60,'transporter','subcategory_management','delete',1,'2026-02-04 19:54:15.770970','2026-02-04 19:54:15.771224'),(61,'seller','polish_management','create',1,'2026-02-04 19:54:17.256709','2026-02-20 04:58:08.466280'),(62,'transporter','polish_management','create',1,'2026-02-04 19:54:17.934304','2026-02-04 19:54:17.934572'),(63,'transporter','polish_management','read',1,'2026-02-04 19:54:18.519951','2026-02-04 19:54:18.520227'),(64,'seller','polish_management','read',1,'2026-02-04 19:54:19.543433','2026-02-20 04:58:08.531534'),(65,'seller','polish_management','update',1,'2026-02-04 19:54:20.101989','2026-02-20 04:58:08.597874'),(66,'transporter','polish_management','update',1,'2026-02-04 19:54:20.855984','2026-02-04 19:54:20.856243'),(67,'seller','polish_management','delete',1,'2026-02-04 19:54:21.859015','2026-02-20 04:58:08.662205'),(68,'transporter','polish_management','delete',1,'2026-02-04 19:54:22.481389','2026-02-04 19:54:22.481578'),(69,'admin','polish_management','delete',1,'2026-02-04 19:54:23.324971','2026-02-19 09:47:57.355355'),(70,'admin','polish_management','update',1,'2026-02-04 19:54:23.898978','2026-02-19 09:47:57.285158'),(71,'admin','polish_management','read',1,'2026-02-04 19:54:24.492951','2026-02-19 09:47:57.215066'),(72,'admin','polish_management','create',1,'2026-02-04 19:54:25.057412','2026-02-19 09:47:57.128459'),(73,'seller','branch_management','create',1,'2026-02-17 10:52:04.251643','2026-02-20 04:58:07.676441'),(74,'seller','branch_management','read',1,'2026-02-17 10:52:04.320122','2026-02-20 04:58:07.744008'),(75,'seller','branch_management','update',1,'2026-02-17 10:52:04.393499','2026-02-20 04:58:07.809125'),(76,'seller','branch_management','delete',1,'2026-02-17 10:52:04.459726','2026-02-20 04:58:07.871134'),(77,'seller','product_management','create',1,'2026-02-17 10:52:05.331425','2026-02-20 04:58:08.728189'),(78,'seller','product_management','read',1,'2026-02-17 10:52:05.395152','2026-02-20 04:58:08.793041'),(79,'seller','product_management','update',1,'2026-02-17 10:52:05.459333','2026-02-20 04:58:08.858450'),(80,'seller','product_management','delete',1,'2026-02-17 10:52:05.520032','2026-02-20 04:58:08.922862'),(81,'seller','product_image_management','create',1,'2026-02-17 10:52:05.579456','2026-02-20 04:58:08.988254'),(82,'seller','product_image_management','read',1,'2026-02-17 10:52:05.650759','2026-02-20 04:58:09.051884'),(83,'seller','product_image_management','update',1,'2026-02-17 10:52:05.709929','2026-02-20 04:58:09.116027'),(84,'seller','product_image_management','delete',1,'2026-02-17 10:52:05.779304','2026-02-20 04:58:09.179564'),(85,'admin','branch_management','create',1,'2026-02-19 09:46:59.078775','2026-02-19 09:47:56.182262'),(86,'admin','branch_management','read',1,'2026-02-19 09:46:59.157997','2026-02-19 09:47:56.261484'),(87,'admin','branch_management','update',1,'2026-02-19 09:46:59.238122','2026-02-19 09:47:56.331554'),(88,'admin','branch_management','delete',1,'2026-02-19 09:46:59.317443','2026-02-19 09:47:56.418137'),(89,'admin','product_management','create',1,'2026-02-19 09:47:00.279733','2026-02-19 09:47:57.424961'),(90,'admin','product_management','read',1,'2026-02-19 09:47:00.352233','2026-02-19 09:47:57.493667'),(91,'admin','product_management','update',1,'2026-02-19 09:47:00.423258','2026-02-19 09:47:57.569759'),(92,'admin','product_management','delete',1,'2026-02-19 09:47:00.493569','2026-02-19 09:47:57.642912'),(93,'admin','product_image_management','create',1,'2026-02-19 09:47:00.582976','2026-02-19 09:47:57.738205'),(94,'admin','product_image_management','read',1,'2026-02-19 09:47:00.662198','2026-02-19 09:47:57.805280'),(95,'admin','product_image_management','update',1,'2026-02-19 09:47:00.738222','2026-02-19 09:47:57.880596'),(96,'admin','product_image_management','delete',1,'2026-02-19 09:47:00.816181','2026-02-19 09:47:57.971921'),(97,'buyer','branch_management','create',1,'2026-02-19 09:53:46.820878','2026-02-20 05:24:21.004972'),(98,'buyer','branch_management','read',1,'2026-02-19 09:53:46.887542','2026-02-20 05:24:21.087740'),(99,'buyer','branch_management','update',1,'2026-02-19 09:53:46.956794','2026-02-20 05:24:21.159064'),(100,'buyer','branch_management','delete',1,'2026-02-19 09:53:47.025536','2026-02-20 05:24:21.228696');
/*!40000 ALTER TABLE `brokers_app_rolepermission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_subcategorymaster`
--

DROP TABLE IF EXISTS `brokers_app_subcategorymaster`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_subcategorymaster` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `subcategory_name` varchar(100) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_subcategorymaster`
--

LOCK TABLES `brokers_app_subcategorymaster` WRITE;
/*!40000 ALTER TABLE `brokers_app_subcategorymaster` DISABLE KEYS */;
INSERT INTO `brokers_app_subcategorymaster` VALUES (1,'moon','2026-02-09 07:02:37.912863','2026-02-09 07:02:37.912898',1),(2,'Methi Seeds','2026-02-19 07:12:57.965660','2026-02-19 07:12:57.965735',1),(3,'chana','2026-02-20 05:15:47.691127','2026-02-20 05:15:47.691161',1),(4,'chia seeds','2026-02-20 05:22:16.610392','2026-02-20 05:22:16.610435',1),(5,'sabja seeds','2026-02-20 05:22:39.281339','2026-02-20 05:22:39.281377',1),(6,'papaya seeds','2026-02-20 05:23:10.453928','2026-02-20 05:23:10.453964',1),(7,'white rice','2026-02-20 10:54:21.120392','2026-02-20 10:54:21.120431',1),(8,'brown rice','2026-02-20 15:55:52.024787','2026-02-20 15:55:52.024823',1);
/*!40000 ALTER TABLE `brokers_app_subcategorymaster` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `brokers_app_tagmaster`
--

DROP TABLE IF EXISTS `brokers_app_tagmaster`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `brokers_app_tagmaster` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tag_name` varchar(50) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `tag_name` (`tag_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `brokers_app_tagmaster`
--

LOCK TABLES `brokers_app_tagmaster` WRITE;
/*!40000 ALTER TABLE `brokers_app_tagmaster` DISABLE KEYS */;
/*!40000 ALTER TABLE `brokers_app_tagmaster` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_brokers_app_daaluser_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_brokers_app_daaluser_id` FOREIGN KEY (`user_id`) REFERENCES `brokers_app_daaluser` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
INSERT INTO `django_admin_log` VALUES (1,'2026-02-09 08:32:48.324558','1','moon - 9993949081',3,'',9,1),(2,'2026-02-16 14:13:44.559421','7','kanhaiya_45',1,'[{\"added\": {}}]',7,1),(3,'2026-02-17 10:41:11.536655','1','1234567890',2,'[{\"changed\": {\"fields\": [\"Is admin\", \"Is superuser\", \"Is staff\"]}}]',7,1),(4,'2026-02-17 10:46:33.208497','1','1234567890',2,'[{\"changed\": {\"fields\": [\"Is superuser\"]}}]',7,10),(5,'2026-02-17 12:03:29.370839','2','9993949080',2,'[{\"changed\": {\"fields\": [\"Kyc status\"]}}]',7,10),(6,'2026-02-19 05:55:05.179589','7','kanhaiya_45',3,'',7,10),(7,'2026-02-19 06:03:57.106885','15','9325371176',3,'',7,10),(8,'2026-02-19 06:17:24.241262','16','9325371176',3,'',7,10),(9,'2026-02-19 09:42:24.585970','17','9325371176',3,'',7,10),(10,'2026-02-20 15:35:28.519878','3','9993949081',2,'[{\"changed\": {\"fields\": [\"Email\", \"Kyc status\"]}}]',7,10),(11,'2026-02-20 15:35:37.402184','3','9993949081',2,'[]',7,10),(12,'2026-02-20 15:42:49.860990','10','daalbroker',2,'[{\"changed\": {\"fields\": [\"Role\"]}}]',7,10);
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (1,'admin','logentry'),(2,'auth','group'),(3,'auth','permission'),(13,'authtoken','token'),(14,'authtoken','tokenproxy'),(15,'brokers_app','branchmaster'),(18,'brokers_app','brandmaster'),(6,'brokers_app','categorymaster'),(19,'brokers_app','contract'),(7,'brokers_app','daaluser'),(8,'brokers_app','polishmaster'),(9,'brokers_app','product'),(10,'brokers_app','productimage'),(16,'brokers_app','productinterest'),(17,'brokers_app','productvideo'),(11,'brokers_app','rolepermission'),(12,'brokers_app','subcategorymaster'),(20,'brokers_app','tagmaster'),(4,'contenttypes','contenttype'),(5,'sessions','session');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=89 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (46,'contenttypes','0001_initial','2026-02-25 12:58:27.358779'),(47,'contenttypes','0002_remove_content_type_name','2026-02-25 12:58:27.362703'),(48,'auth','0001_initial','2026-02-25 12:58:27.367333'),(49,'auth','0002_alter_permission_name_max_length','2026-02-25 12:58:27.371077'),(50,'auth','0003_alter_user_email_max_length','2026-02-25 12:58:27.374899'),(51,'auth','0004_alter_user_username_opts','2026-02-25 12:58:27.378850'),(52,'auth','0005_alter_user_last_login_null','2026-02-25 12:58:27.382124'),(53,'auth','0006_require_contenttypes_0002','2026-02-25 12:58:27.384873'),(54,'auth','0007_alter_validators_add_error_messages','2026-02-25 12:58:27.387777'),(55,'auth','0008_alter_user_username_max_length','2026-02-25 12:58:27.391239'),(56,'auth','0009_alter_user_last_name_max_length','2026-02-25 12:58:27.393943'),(57,'auth','0010_alter_group_name_max_length','2026-02-25 12:58:27.396640'),(58,'auth','0011_update_proxy_permissions','2026-02-25 12:58:27.399454'),(59,'auth','0012_alter_user_first_name_max_length','2026-02-25 12:58:27.402594'),(60,'brokers_app','0001_initial','2026-02-25 12:58:27.406059'),(61,'admin','0001_initial','2026-02-25 12:58:27.409701'),(62,'admin','0002_logentry_remove_auto_add','2026-02-25 12:58:27.413689'),(63,'admin','0003_logentry_add_action_flag_choices','2026-02-25 12:58:27.416737'),(64,'authtoken','0001_initial','2026-02-25 12:58:27.419995'),(65,'authtoken','0002_auto_20160226_1747','2026-02-25 12:58:27.423097'),(66,'authtoken','0003_tokenproxy','2026-02-25 12:58:27.425933'),(67,'authtoken','0004_alter_tokenproxy_options','2026-02-25 12:58:27.429436'),(68,'brokers_app','0002_daaluser_is_transporter','2026-02-25 12:58:27.433716'),(69,'brokers_app','0003_rename_is_broker_daaluser_is_buyer_and_more','2026-02-25 12:58:27.437797'),(70,'brokers_app','0004_daaluser_plain_text_password_temp','2026-02-25 12:58:27.442062'),(71,'brokers_app','0005_remove_daaluser_plain_text_password_temp_and_more','2026-02-25 12:58:27.447221'),(72,'brokers_app','0006_daaluser_gst_number_daaluser_is_both_sellerandbuyer_and_more','2026-02-25 12:58:27.451165'),(73,'brokers_app','0007_categorymaster','2026-02-25 12:58:27.455427'),(74,'brokers_app','0008_alter_daaluser_gst_number_alter_daaluser_pan_number','2026-02-25 12:58:27.458797'),(75,'brokers_app','0009_remove_categorymaster_subtype_and_more','2026-02-25 12:58:27.462503'),(76,'brokers_app','0010_polishmaster','2026-02-25 12:58:27.465678'),(77,'brokers_app','0011_product_productimage','2026-02-25 12:58:27.469097'),(78,'brokers_app','0012_alter_daaluser_mobile','2026-02-25 12:58:27.472504'),(79,'brokers_app','0013_rolepermission','2026-02-25 12:58:27.476168'),(80,'brokers_app','0014_daaluser_brand_daaluser_company_name_daaluser_dob_and_more','2026-02-25 12:58:27.479773'),(81,'brokers_app','0015_branchmaster_productinterest_daaluser_account_status_and_more','2026-02-25 12:58:27.483645'),(82,'brokers_app','0016_alter_daaluser_account_status_alter_daaluser_status','2026-02-25 12:58:27.487969'),(83,'brokers_app','0017_productvideo','2026-02-25 12:58:27.492125'),(84,'brokers_app','0018_categorymaster_is_active_product_video_and_more','2026-02-25 12:58:27.495061'),(85,'brokers_app','0019_alter_daaluser_gst_image_alter_daaluser_pan_image','2026-02-25 12:58:27.498286'),(86,'brokers_app','0020_brandmaster_contract_tagmaster_and_more','2026-02-25 12:58:27.502437'),(87,'brokers_app','0021_alter_product_amount','2026-02-25 12:58:27.505154'),(88,'sessions','0001_initial','2026-02-25 12:58:27.507890');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
INSERT INTO `django_session` VALUES ('33qfqqgg4zljnnfctwsgh7akv8snee1t','.eJxVizsOwjAMQO-SGVW16zSYkZ0zRDF2lKqIVgmdEHdHlTrA-j5vF9P2KnFrVuOk7uLAnX6ZpPtsz11IXWarLaZ17Q7autsi08OuR_R3ltTKvpmOyYsCyxnRzHomGwDFMAAQcwDqVZBBBw1C4D0bas4BKdMI7vMFTgo1LQ:1vrUjH:R1XlvyE3ewOpYsterI1gJOPXIbKrBP931eq9YYZxt9s','2026-03-01 05:31:35.546482'),('5rg2jygep2vw11gmnibopqzurv4pl5io','.eJxVizsOwjAMQO-SGVW16zSYkZ0zRDF2lKqIVgmdEHdHlTrA-j5vF9P2KnFrVuOk7uLAnX6ZpPtsz11IXWarLaZ17Q7autsi08OuR_R3ltTKvpmOyYsCyxnRzHomGwDFMAAQcwDqVZBBBw1C4D0bas4BKdMI7vMFTgo1LQ:1vnymd:NxoeMCvF7lCEcYOQYvR6OxarCadYvrQmDBfj-9l1-ks','2026-02-19 12:48:31.745700'),('8nsu8wony3yz4ptt9gnspigmu7m00wmy','.eJxVizsOwjAMQO-SGVX5mMRhZOcMkeM6SlVEq4ROiLtTpA6wvs9LJdqeNW1dWppGdVFGq9MvzMSzPL4mt2WW1hOt63DQPtyWPN3lekR_Z6Ve9y3EWAQDO0brIBKNwIW9tijWuADxHDVq8EDZ7aUfgahYF60gArNR7w9aoDVJ:1vtKWY:N7zNrsAUoOtZ1OvnuykCA2Iu3-c1MqH5jD3QPW0k5aQ','2026-03-06 07:02:02.177459'),('9gtxitxcp100cr54g8i221f7vb1vdtgt','.eJxVizsOwjAMQO-SGVW16zSYkZ0zRDF2lKqIVgmdEHdHlTrA-j5vF9P2KnFrVuOk7uLAnX6ZpPtsz11IXWarLaZ17Q7autsi08OuR_R3ltTKvpmOyYsCyxnRzHomGwDFMAAQcwDqVZBBBw1C4D0bas4BKdMI7vMFTgo1LQ:1vnXWW:DO3A9BkRQPeRAN5tDvfmTDyaPbSnHQT1ncJclZfuels','2026-02-18 07:42:04.119317'),('bbom6pi4y83xt0ab2ma28t5hu4v2771h','.eJxVizsOwjAMQO-SGVVx0vwY2TlDZDtGqYpolbQT4u6A1AHW93mqjPtW896l5amoszLq9MsIeZbHV1BbZmk947oOB-3DdaHpLpcj-jsr9vrZkHwCH5LxkBBM8GBYAIuLELwDT2w5RD3eLJWRYyTW2iJAtOBCRFGvNxsjNGQ:1vnirq:u7e2KsxHb1isAo7tDGhUHVaAtPnDgbVB5U0uBvsgdPY','2026-02-18 19:48:50.196863'),('cdeb46nfmluqd831ce3jiv3e2n5a7lzr','.eJxVizsOwjAQBe_iGkXxb-2lpOcM1q4_chREIjupEHcnSCmgfPNmXiLQvtWw99zClMRVaHH5ZUxxzs_vwW2Zc-uB1nU4aR_uC0-PfDulv7JSr0dmTULW2hk1em_HYlgSOOUZChKgt5g9JYdGolaqyMgqH9MB6AgSrHh_ABnvNDc:1vtQyS:OmMqRbZVVNL7pxGyyCM4_xccEEZpanlI81tnFl9hHjc','2026-03-06 13:55:16.073296'),('cr6itxzbn0m3uusweh7amkinsseelxd5','.eJxVizsOwjAMQO-SGVX5mMRhZOcMkeM6SlVEq4ROiLtTpA6wvs9LJdqeNW1dWppGdVFGq9MvzMSzPL4mt2WW1hOt63DQPtyWPN3lekR_Z6Ve9y3EWAQDO0brIBKNwIW9tijWuADxHDVq8EDZ7aUfgahYF60gArNR7w9aoDVJ:1vtNsT:-8mue7Kb7M7-ONXKyWgrPG6ZezXD2yJ2SdWEBq0g7M8','2026-03-06 10:36:53.145370'),('ee1lfv8jdrorzhu58ufocvvvr0ozm3t5','.eJxVizsOwjAMQO-SGVVx0vwY2TlDZDtGqYpolbQT4u6A1AHW93mqjPtW896l5amoszLq9MsIeZbHV1BbZmk947oOB-3DdaHpLpcj-jsr9vrZkHwCH5LxkBBM8GBYAIuLELwDT2w5RD3eLJWRYyTW2iJAtOBCRFGvNxsjNGQ:1vnyon:k2vZKSVBFQrAVTmQ1vNqQ4gCmHixiD-9bYf_e_cRIRM','2026-02-19 12:50:45.698729'),('ev1aol5xwx2d0sn7duxyk6we6n979g6y','.eJxVizsOwjAMQO-SGVX5mMRhZOcMkeM6SlVEq4ROiLtTpA6wvs9LJdqeNW1dWppGdVFGq9MvzMSzPL4mt2WW1hOt63DQPtyWPN3lekR_Z6Ve9y3EWAQDO0brIBKNwIW9tijWuADxHDVq8EDZ7aUfgahYF60gArNR7w9aoDVJ:1vtRs9:i2XWKOTat3wztIIgZgs6kBsO5uwRjyzIigljKfloOts','2026-03-06 14:52:49.188269'),('j2wqm1sc44aff8jpb7h6et74vg2lmkjl','.eJxVjDsOwjAQBe_iGkXr32Io6TmDtWuv5SiIRHZSIe4OkVJAO_PmvVSkba1x69LimNVVaa1Ov5ApTfLcDbd5ktYjLctw0D7cZx4fcjtGf2WlXvdDwwAF_AV0wZBtQLZWNAOLQa_ZGUafwOqQib7KCqRUhMkZh2c06v0BTDc1MA:1vv9lG:HOQ1g3GHl-0QIrpLU_zGApmoANnaUTVaa2ROT9AurS0','2026-03-11 07:56:46.446323'),('l209k1y8bqnufypt16sla2b9lokeclzi','.eJxVizsOwjAMQO-SGVW16zSYkZ0zRDF2lKqIVgmdEHdHlTrA-j5vF9P2KnFrVuOk7uLAnX6ZpPtsz11IXWarLaZ17Q7autsi08OuR_R3ltTKvpmOyYsCyxnRzHomGwDFMAAQcwDqVZBBBw1C4D0bas4BKdMI7vMFTgo1LQ:1vnY3e:V1UBEnUOw9Dpk1kzQBCxsu1YQuqAktWXWI37ShtuFwM','2026-02-18 08:16:18.829087'),('madnkpralxstx0u3uop19xoa2oedd1u5','.eJxVizsOwjAMQO-SGVX5mMRhZOcMkeM6SlVEq4ROiLtTpA6wvs9LJdqeNW1dWppGdVFGq9MvzMSzPL4mt2WW1hOt63DQPtyWPN3lekR_Z6Ve9y3EWAQDO0brIBKNwIW9tijWuADxHDVq8EDZ7aUfgahYF60gArNR7w9aoDVJ:1vtI4n:DoNzKogQlcxhYPmhHqxFYM8GAwfjw5fwjbdi5841wn4','2026-03-06 04:25:13.838594'),('o6jpenz2cqjlz074d84yn8gpvgvz45nh','.eJxVjDsOwjAQBe_iGkXr32Io6TmDtWuv5SiIRHZSIe4OkVJAO_PmvVSkba1x69LimNVVaa1Ov5ApTfLcDbd5ktYjLctw0D7cZx4fcjtGf2WlXvdDwwAF_AV0wZBtQLZWNAOLQa_ZGUafwOqQib7KCqRUhMkZh2c06v0BTDc1MA:1vtPKb:SS2WSRzIo1o93sdNb8v9Dw61EgWkB3fE0kXW4481jEo','2026-03-06 12:10:01.369570'),('plsfnqhal6htmhssozqi3ohc6f5znkrq','.eJxVi0sOwiAQQO_C2jTA8HXp3jMQhhlCU2MbsCvj3dWkC92-z1OkvD9a2gf3NJM4CyXF6RdiLgvfvwb7unAfKW_bdNAxXVecb3w5or-z5dE-G0mFXEhSBO8MuaKLCZ4DK_RgY9DE1hdtXfSsIxSuAMFDNBWJKkvxegNtxDXg:1vsZkM:0Fa850CE9P-uuwPLKuYS8XqKp6-P5d-Jps1u9ttdRpI','2026-03-04 05:05:10.227474'),('qi2jtkj5t0rexwgr54m373clqluj8b1a','.eJxVizsOwjAMQO-SGVW16zSYkZ0zRDF2lKqIVgmdEHdHlTrA-j5vF9P2KnFrVuOk7uLAnX6ZpPtsz11IXWarLaZ17Q7autsi08OuR_R3ltTKvpmOyYsCyxnRzHomGwDFMAAQcwDqVZBBBw1C4D0bas4BKdMI7vMFTgo1LQ:1vpgRv:J69mo7BSjdwGcCWAgWExNXQKgCEDtRFB47qRArpP2zE','2026-02-24 05:38:11.790150'),('rymy9j1zu65xzdn1vvyudnpofrburxug','.eJxVi0sOwiAQhu_C2jTQKaTj0r1nIDP0JzQ1tgG7Mt5dTbrQ7fd4mij7o8S9ocZ5MmfjRnP6hSppwf1rtK4Laouybd1BW3dddb7hckR_Z5FWPptMji1ZJdWRIYSBfbA2-8wpBQyBIAyfkHt41uAImTU7TSK9JTGvN4K6Nq4:1vtNV0:VK2l1IK2otssVUoPzhotRAP8giGBJKQzEW6Kt11Gc8o','2026-03-06 10:12:38.541685'),('ug3saqofrjpfzrjg68diuscvxoucrqmt','.eJxVizsOwjAQBe_iGkXxb-2lpOcM1q4_chREIjupEHcnSCmgfPNmXiLQvtWw99zClMRVaHH5ZUxxzs_vwW2Zc-uB1nU4aR_uC0-PfDulv7JSr0dmTULW2hk1em_HYlgSOOUZChKgt5g9JYdGolaqyMgqH9MB6AgSrHh_ABnvNDc:1vtSYR:_Bo8vrBwu9TGQikW536YYsnVqVVQaOMRxY4sMJkCKqU','2026-03-06 15:36:31.974417'),('w4ntvq08r29hj4u687zs6cgxkie0jgd5','.eJxVjEEOwiAQRe_C2pDOFIq4dN8zEKYzSNVAUtqV8e7apAvd_vfef6kQtzWHrckSZlYXBer0u1GcHlJ2wPdYblVPtazLTHpX9EGbHivL83q4fwc5tvytSXiIlhg8nRFFpPNGekASdADGewemY0IP3LMjA9Z6QU7JoUlmAPX-AOu9N6A:1vrzKE:EhoFssRUVbTZdb1Dr2XNLbA-v85vTbh_uEXIkbewOGI','2026-03-02 14:11:46.870239'),('wdkka5inxlagf2q57b87qc9fxutmgrnq','.eJxVizsOwjAQBe_iGkWO1_hDSc8ZrF17V46CSGSTCnF3gpQCitfMm3mphNuzpq1zS1NRF2XV6ZcR5pkf34PaMnPrCdd1OGgfbgtNd74e0l9Zsdc9yySjRGu8A_AeNeZRMATtCEyMZ1PIO-uASxGCYvZ5cBKiMGjnGdT7A0ZTNXM:1vtSbQ:C4Tj3fKz1_OE4gWCRyAziku_3XzHpTwC3HCpF7ozq3M','2026-03-06 15:39:36.814282'),('wl4t982h6jjb2ukvmnm0dbg7duj22suh','.eJxVizsOwjAMQO-SGVVx0vwY2TlDZDtGqYpolbQT4u6A1AHW93mqjPtW896l5amoszLq9MsIeZbHV1BbZmk947oOB-3DdaHpLpcj-jsr9vrZkHwCH5LxkBBM8GBYAIuLELwDT2w5RD3eLJWRYyTW2iJAtOBCRFGvNxsjNGQ:1vtScq:ZINNBwHKuYe4qxZMhLPekbt2BpqQ741KSzBlg4LRIMY','2026-03-06 15:41:04.828196'),('wxg5jzwzcw65zj9wj9ri9avxlrkipkso','.eJxVi0sOwiAQhu_C2jTQKaTj0r1nIDP0JzQ1tgG7Mt5dTbrQ7fd4mij7o8S9ocZ5MmfjRnP6hSppwf1rtK4Laouybd1BW3dddb7hckR_Z5FWPptMji1ZJdWRIYSBfbA2-8wpBQyBIAyfkHt41uAImTU7TSK9JTGvN4K6Nq4:1vtNV1:tTqFBtOOerPDcGWnWyK3TC5Kvet4f6xIHPPGJanelTw','2026-03-06 10:12:39.791937'),('y9knvwa26ak6if7qlxqy4k8jgrm4ams6','.eJxVizsOwjAMQO-SGVW16zSYkZ0zRDF2lKqIVgmdEHdHlTrA-j5vF9P2KnFrVuOk7uLAnX6ZpPtsz11IXWarLaZ17Q7autsi08OuR_R3ltTKvpmOyYsCyxnRzHomGwDFMAAQcwDqVZBBBw1C4D0bas4BKdMI7vMFTgo1LQ:1vnXJg:ksNXqv-mS5CEy4oIciz2AqTV-Q87pZ007YmsxY2v--k','2026-02-18 07:28:48.152724');
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-02-25 13:04:48
