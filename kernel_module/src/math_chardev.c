#include <linux/module.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/uaccess.h>
#include <linux/overflow.h>
#include <linux/mutex.h>

#define DEVICE_NAME "math_chardev"
#define DEVICE_MAJOR 0 // Dynamic major number allocation

#ifndef S32_MAX
#define S32_MAX 2147483647
#endif

#ifndef S32_MIN
#define S32_MIN (-S32_MAX - 1)
#endif

static DEFINE_MUTEX(calc_mutex);

static int32_t device_major;
static struct cdev math_chardev_cdev;

typedef int32_t calc_int_t; // Type for the operands
static char calc_result[256];
static ssize_t calc_result_size = 100;

// Initialize resources
static int32_t math_chardev_open(struct inode *inode, struct file *file);

// Free resources
static int32_t math_chardev_release(struct inode *inode, struct file *file);

// Call when data is read from the device
static ssize_t math_chardev_read(struct file *file, char __user *user_buf,
				 size_t count, loff_t *ppos);

// Call when write to device
static ssize_t math_chardev_write(struct file *file,
				  const char __user *user_buf, size_t count,
				  loff_t *ppos);

// Init in kernel, allocation a major number, cdev_add - add char dev
static int32_t __init math_chardev_init(void);

// Exit in kernel, unregister the major number
static void __exit math_chardev_exit(void);

static int32_t math_chardev_open(struct inode *inode, struct file *file)
{
	if (!mutex_trylock(&calc_mutex)) {
		// The device is already in use
		return -EBUSY;
	}
	printk(KERN_NOTICE "math_chardev: =-Device opened!\n");

	return 0;
}

static int32_t math_chardev_release(struct inode *inode, struct file *file)
{
	printk(KERN_NOTICE "math_chardev: =-Device released!\n");
	// Release the mutex so the device can be used by other program
	mutex_unlock(&calc_mutex);
	return 0;
}

static ssize_t math_chardev_read(struct file *file, char __user *user_buf,
				 size_t count, loff_t *ppos)
{
	size_t bytes_to_read;
	printk(KERN_DEBUG
	       "math_chardev: Read called with count = %zu, ppos = %lld\n",
	       count, *ppos);

	if (count < calc_result_size) {
		printk(KERN_DEBUG "math_chardev: Buffer too small\n");
		return 0;
	}

	if (*ppos >= calc_result_size) {
		printk(KERN_DEBUG "math_chardev: No more data to read\n");
		return 0;
	}

	bytes_to_read = min((size_t)(calc_result_size - *ppos), count);

	if (copy_to_user(user_buf, calc_result + *ppos, bytes_to_read)) {
		printk(KERN_ERR "math_chardev: Error copying to user space\n");
		return -EFAULT;
	}

	printk(KERN_DEBUG "math_chardev: Successfully read data: %s\n",
	       calc_result);

	*ppos += bytes_to_read;
	// *ppos = 0;
	return bytes_to_read;
}

loff_t math_chardev_llseek(struct file *file, loff_t offset, int whence)
{
	loff_t newpos;

	switch (whence) {
	case 0: /* SEEK_SET */
		newpos = offset;
		break;

	case 1: /* SEEK_CUR */
		newpos = file->f_pos + offset;
		break;

	case 2: /* SEEK_END */
		// For your device, this could mean the end of your data buffer
		newpos = calc_result_size + offset;
		break;

	default: /* can't happen */
		return -EINVAL;
	}

	if (newpos < 0 || newpos > calc_result_size)
		return -EINVAL;

	file->f_pos = newpos;
	return newpos;
}

static ssize_t math_chardev_write(struct file *file,
				  const char __user *user_buf, size_t count,
				  loff_t *ppos)
{
	char buf[128];
	char operator;
	calc_int_t operand1, operand2;
	calc_int_t result = 0;
	int64_t long_operand1;
	int64_t long_operand2;
	int32_t scan_result;
	char extra_char;

	printk(KERN_INFO "math_chardev: Write called with count = %zu\n",
	       count);

	if (count >= sizeof(buf)) {
		printk(KERN_DEBUG "math_chardev: Write buffer overflow\n");
		return -EINVAL;
	}

	if (copy_from_user(buf, user_buf, count)) {
		printk(KERN_DEBUG "math_chardev: Error copying from user\n");
		return -EFAULT;
	}

	buf[count] = '\0';

	printk(KERN_INFO "math_chardev: Received string from user: %s\n", buf);

	scan_result = sscanf(buf, "%lld %c %lld %c", &long_operand1,
			     &operator, & long_operand2, &extra_char);

	if (scan_result != 3) {
		printk(KERN_ERR
		       "math_chardev: Parsing error or extra input detected\n");
		return -EDOM;
	}

	// Check for parentheses in the input
	if (strchr(buf, '(') || strchr(buf, ')')) {
		printk(KERN_INFO
		       "math_chardev: Parentheses detected in input.\n");
		printk(KERN_INFO
		       "math_chardev: With two operands, parentheses do not alter the order of operations.\n");
		return -EDOM;
	}

	if (sscanf(buf, "%lld %c %lld", &long_operand1,
		   &operator, & long_operand2) != 3) {
		printk(KERN_DEBUG "math_chardev: Parsing error\n");
		return -EDOM;
	}

	if (long_operand1 < S32_MIN || long_operand1 > S32_MAX ||
	    long_operand2 < S32_MIN || long_operand2 > S32_MAX) {
		printk(KERN_DEBUG "math_chardev: Operand range error\n");
		return -ERANGE;
	}

	operand1 = (calc_int_t)long_operand1;
	operand2 = (calc_int_t)long_operand2;

	switch (operator) {
	case '+':
		if (check_add_overflow(operand1, operand2, &result)) {
			printk(KERN_DEBUG "math_chardev: Addition overflow\n");
			return -ERANGE;
		}
		result = operand1 + operand2;
		break;
	case '-':
		if (check_sub_overflow(operand1, operand2, &result)) {
			printk(KERN_DEBUG
			       "math_chardev: Subtraction overflow\n");
			return -ERANGE;
		}
		result = operand1 - operand2;
		break;
	case '*':
		if (check_mul_overflow(operand1, operand2, &result)) {
			printk(KERN_DEBUG
			       "math_chardev: Multiplication overflow\n");
			return -EOVERFLOW;
		}
		result = operand1 * operand2;
		break;
	case '/':
		// Check for division overflow
		if (operand2 == 0 || (operand1 == INT_MIN && operand2 == -1)) {
			printk(KERN_DEBUG
			       "math_chardev: Division by zero or overflow\n");
			return -EOVERFLOW;
		}
		result = operand1 / operand2;
		break;
	default:
		printk(KERN_DEBUG "math_chardev: Invalid operator\n");
		return -EINVAL;
	}

	printk(KERN_DEBUG "math_chardev: Calculation result = %d\n", result);

	calc_result_size =
		snprintf(calc_result, sizeof(calc_result), "%d\n", result);

	return count;
}

static const struct file_operations math_chardev_fops = {
	.owner = THIS_MODULE,
	.open = math_chardev_open,
	.release = math_chardev_release,
	.read = math_chardev_read,
	.write = math_chardev_write,
	.llseek = math_chardev_llseek,
};

static int32_t __init math_chardev_init(void)
{
	int32_t result;
	dev_t dev;

	// Allocating major number
	result = alloc_chrdev_region(&dev, 0, 1, DEVICE_NAME);
	device_major = MAJOR(dev);

	if (result < 0) {
		printk(KERN_DEBUG "math_chardev: can't get major %d\n",
		       device_major);
		return result;
	}

	cdev_init(&math_chardev_cdev, &math_chardev_fops);
	math_chardev_cdev.owner = THIS_MODULE;
	result = cdev_add(&math_chardev_cdev, dev, 1);

	if (result) {
		printk(KERN_DEBUG "Error %d adding math_chardev", result);
		unregister_chrdev_region(dev, 1);
		return result;
	}

	printk(KERN_DEBUG "math_chardev: registered with major number %d\n",
	       device_major);
	return 0;
}

static void __exit math_chardev_exit(void)
{
	cdev_del(&math_chardev_cdev);
	unregister_chrdev_region(MKDEV(device_major, 0), 1);
	printk(KERN_DEBUG "math_chardev: unregistered\n");
}

module_init(math_chardev_init);
module_exit(math_chardev_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Simeon Baltadzhiev");
MODULE_DESCRIPTION("Basic math operations char device");
MODULE_VERSION("0:1.0");
